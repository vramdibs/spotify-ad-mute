from enum import Enum
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time


class Decision(Enum):
    NONE = "none"
    NEXT = "next"
    MUTE = "mute"
    UNMUTE = "unmute"


class Watcher:
    def __init__(self):
        self.armed_uri = None
        self.arm_at = None
        self.muted = False
        self.mute_applied = False

    def on_uri(self, uri, now):
        if isinstance(uri, str) and uri.startswith("spotify:ad:"):
            if self.armed_uri != uri:
                self.armed_uri = uri
                self.arm_at = now
                self.mute_applied = False
                return Decision.NEXT
            if (
                not self.mute_applied
                and self.arm_at is not None
                and now >= self.arm_at + 1.0
            ):
                self.muted = True
                self.mute_applied = True
                return Decision.MUTE
            return Decision.NONE
        if self.muted:
            self.muted = False
            self.mute_applied = False
            self.armed_uri = None
            self.arm_at = None
            return Decision.UNMUTE
        self.armed_uri = None
        self.arm_at = None
        self.mute_applied = False
        return Decision.NONE


class LogCursor:
    def __init__(self):
        self._uri = None

    def feed(self, line):
        if "track_uri:" in line:
            self._uri = line.split("track_uri:", 1)[1].strip()
            return None
        if "ad: yes" in line and isinstance(self._uri, str) and self._uri.startswith("spotify:ad:"):
            return self._uri
        if "ad: no" in line and isinstance(self._uri, str) and self._uri.startswith("spotify:track:"):
            return self._uri
        return None


def decide_after(watcher, uri, now, sleep_fn, read_again_fn):
    first = watcher.on_uri(uri, now)
    actions = [first]
    if first is Decision.NEXT:
        sleep_fn(1.0)
        actions.append(watcher.on_uri(read_again_fn(), now + 1.0))
    return actions


LOG_PATH = Path.home() / ".var/app/com.spotify.Client/data/spotify-ad.log"


def spotify_sink_ids(sink_inputs):
    found = []
    for item in sink_inputs:
        props = item.get("properties") or {}
        binary = props.get("application.process.binary", "")
        name = props.get("application.name", "")
        if binary == "spotify" or name == "Spotify":
            found.append(int(item["index"]))
    return found


def build_spotify_argv(log_mode, log_path):
    argv = ["flatpak", "run", "com.spotify.Client"]
    if log_mode:
        argv.append("--log-file=%s" % log_path)
        argv.append("--debug-level=1")
    return argv


def truncate_log(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")


def uri_from_mpris_line(line):
    text = line.strip()
    if text.startswith("spotify:ad:") or text.startswith("spotify:track:"):
        return text
    if text.startswith("/com/spotify/track/"):
        return "spotify:track:" + text.rsplit("/", 1)[-1]
    if text.startswith("/com/spotify/ad/"):
        return "spotify:ad:" + text.rsplit("/", 1)[-1]
    return None


def flatpak_app_running(ps_text, app_id="com.spotify.Client"):
    return app_id in ps_text


def cmdline_has_log(cmd):
    return b"--log-file=" in cmd and b"spotify" in cmd


def ensure_action(running, has_log, lock_free):
    if not lock_free:
        return "busy"
    if running and not has_log:
        return "relaunch"
    if running and has_log:
        return "follow"
    return "launch"


def apply_decision(decision, sink_ids, set_muted, next_fn):
    if decision is Decision.NEXT:
        next_fn()
        return
    if decision is Decision.MUTE:
        for sink_id in sink_ids:
            set_muted(sink_id, True)
        return
    if decision is Decision.UNMUTE:
        for sink_id in sink_ids:
            set_muted(sink_id, False)


def run_child(argv, on_exit):
    proc = subprocess.Popen(argv)
    try:
        return proc.wait()
    finally:
        on_exit()


def session_argv(mpris_seen, log_path):
    if mpris_seen:
        return build_spotify_argv(False, log_path)
    truncate_log(Path(log_path))
    return build_spotify_argv(True, log_path)


def press_next(runner=subprocess.run):
    runner(
        [
            "dbus-send",
            "--session",
            "--type=method_call",
            "--dest=org.mpris.MediaPlayer2.spotify",
            "/org/mpris/MediaPlayer2",
            "org.mpris.MediaPlayer2.Player.Next",
        ],
        check=False,
    )


def reapply_unmute(set_muted, sink_ids_fn, sleep_fn):
    elapsed = 0.0
    for delay in (0.0, 0.3, 1.0):
        if delay > elapsed:
            sleep_fn(delay - elapsed)
            elapsed = delay
        for sink_id in sink_ids_fn():
            set_muted(sink_id, False)


def handle_uri(watcher, uri, now, sleep_fn, next_fn, set_muted, sink_ids_fn):
    for decision in decide_after(watcher, uri, now, sleep_fn, lambda current=uri: current):
        if decision is Decision.UNMUTE:
            reapply_unmute(set_muted, sink_ids_fn, sleep_fn)
            continue
        apply_decision(decision, sink_ids_fn(), set_muted, next_fn)


def apply_historical(watcher, uri, set_muted, sink_ids_fn, sleep_fn, now):
    if isinstance(uri, str) and uri.startswith("spotify:ad:"):
        watcher.armed_uri = uri
        watcher.arm_at = now - 1.0
        watcher.muted = True
        watcher.mute_applied = True
        for sink_id in sink_ids_fn():
            set_muted(sink_id, True)
        return
    if isinstance(uri, str) and uri.startswith("spotify:track:"):
        watcher.muted = False
        watcher.mute_applied = False
        watcher.armed_uri = None
        watcher.arm_at = None
        reapply_unmute(set_muted, sink_ids_fn, sleep_fn)


def catch_up_lines(lines, watcher, now, sleep_fn, next_fn, set_muted, sink_ids_fn):
    del next_fn
    cursor = LogCursor()
    last = None
    for line in lines:
        uri = cursor.feed(line)
        if uri:
            last = uri
    if last:
        apply_historical(watcher, last, set_muted, sink_ids_fn, sleep_fn, now)
    return cursor


def follow_lines(lines, now_fn, sleep_fn, next_fn, set_muted, sink_ids_fn):
    watcher = Watcher()
    cursor = LogCursor()
    for line in lines:
        uri = uri_from_mpris_line(line)
        if uri is None and "ad:" not in line and "track_uri:" not in line:
            continue
        if uri is None:
            uri = cursor.feed(line)
        if not uri:
            continue
        handle_uri(watcher, uri, now_fn(), sleep_fn, next_fn, set_muted, sink_ids_fn)


def first_mpris_uri(lines, elapsed_fn):
    for line in lines:
        uri = uri_from_mpris_line(line)
        if uri:
            return uri
        if elapsed_fn() >= 20:
            return None
    return None


def _pactl_set(sink_id, muted):
    subprocess.run(
        ["pactl", "set-sink-input-mute", str(sink_id), "1" if muted else "0"],
        check=False,
    )


def _live_sink_ids():
    completed = subprocess.run(
        ["pactl", "-f", "json", "list", "sink-inputs"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        payload = payload.get("sink_inputs") or payload.get("sink-inputs") or []
    return spotify_sink_ids(payload)


def release_mute():
    for sink_id in _live_sink_ids():
        _pactl_set(sink_id, False)


def follow_log(still_running, log_path):
    watcher = Watcher()
    with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
        caught = []
        while True:
            line = handle.readline()
            if not line:
                break
            caught.append(line)
        cursor = catch_up_lines(
            caught,
            watcher,
            time.time(),
            time.sleep,
            press_next,
            _pactl_set,
            _live_sink_ids,
        )
        while still_running():
            line = handle.readline()
            if not line:
                time.sleep(0.2)
                continue
            uri = cursor.feed(line)
            if uri:
                handle_uri(
                    watcher,
                    uri,
                    time.time(),
                    time.sleep,
                    press_next,
                    _pactl_set,
                    _live_sink_ids,
                )


def spotify_still_running():
    completed = subprocess.run(
        ["flatpak", "ps", "--columns=application"],
        capture_output=True,
        text=True,
        check=False,
    )
    return flatpak_app_running(completed.stdout or "")


def main():
    log_path = str(LOG_PATH)
    proc = subprocess.Popen(session_argv(False, log_path))
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not spotify_still_running():
            time.sleep(0.2)
        if spotify_still_running():
            follow_log(spotify_still_running, LOG_PATH)
    finally:
        release_mute()
        if proc.poll() is None:
            proc.wait()


def any_cmdline_has_log():
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % name, "rb") as handle:
                cmd = handle.read()
        except OSError:
            continue
        if cmdline_has_log(cmd):
            return True
    return False


def acquire_lock():
    path = Path("/run/user/%s/spotify-ad-watch.lock" % os.getuid())
    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def ensure():
    lock = acquire_lock()
    if lock is None:
        return
    action = ensure_action(spotify_still_running(), any_cmdline_has_log(), True)
    if action == "relaunch":
        subprocess.run(["flatpak", "kill", "com.spotify.Client"], check=False)
        deadline = time.monotonic() + 8
        while spotify_still_running() and time.monotonic() < deadline:
            time.sleep(0.2)
        action = "launch"
    if action == "follow":
        try:
            follow_log(spotify_still_running, LOG_PATH)
        finally:
            release_mute()
        return
    main()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ensure":
        ensure()
    else:
        main()
