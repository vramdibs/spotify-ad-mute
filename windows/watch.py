"""Launch official Spotify on Windows and mute only its audio session."""

from pathlib import Path
import ctypes
from ctypes import c_long, c_ulong, c_void_p, sizeof
import os
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "pc"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import audio_session
import policy
from spotify_ad_watch import LogCursor, Watcher, truncate_log


def log_path():
    return Path(os.environ["LOCALAPPDATA"]) / "spotify-ad-mute" / "spotify-ad.log"


def status_path():
    return log_path().with_name("spotify-ad-watch.status")


def spotify_exe():
    return Path(os.environ["APPDATA"]) / "Spotify" / "Spotify.exe"


def build_argv(path):
    return [str(spotify_exe()), "--log-file=%s" % path, "--debug-level=8"]


def note(text):
    path = status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text + "\n")


class SmtcClient:
    def __init__(self, helper):
        self.disabled = False
        self.proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-File", str(helper)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def _ask(self, command):
        if self.disabled or self.proc.poll() is not None:
            self.disabled = True
            return None
        self.proc.stdin.write(command + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            self.disabled = True
            return None
        return line.strip()

    def title(self):
        line = self._ask("poll")
        if not line or line == "NONE" or line.startswith("ERR"):
            if line and line.startswith("ERR"):
                self.disabled = True
            return None
        if line.startswith("TITLE "):
            return line[6:]
        return None

    def next(self):
        line = self._ask("next")
        return line == "OK"

    def close(self):
        if self.proc.poll() is None:
            try:
                self.proc.stdin.write("quit\n")
                self.proc.stdin.flush()
            except OSError:
                self.proc.kill()


def _toolhelp():
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.argtypes = [c_ulong, c_ulong]
    kernel32.CreateToolhelp32Snapshot.restype = c_void_p
    kernel32.Process32FirstW.argtypes = [c_void_p, c_void_p]
    kernel32.Process32FirstW.restype = c_long
    kernel32.Process32NextW.argtypes = [c_void_p, c_void_p]
    kernel32.Process32NextW.restype = c_long
    kernel32.CloseHandle.argtypes = [c_void_p]
    return kernel32


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", c_ulong),
        ("cntUsage", c_ulong),
        ("th32ProcessID", c_ulong),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", c_ulong),
        ("cntThreads", c_ulong),
        ("th32ParentProcessID", c_ulong),
        ("pcPriClassBase", c_long),
        ("dwFlags", c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def spotify_running():
    kernel32 = _toolhelp()
    snap = kernel32.CreateToolhelp32Snapshot(2, 0)
    if not snap or snap == ctypes.c_void_p(-1).value:
        return False
    entry = PROCESSENTRY32W()
    entry.dwSize = sizeof(PROCESSENTRY32W)
    try:
        found = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while found:
            if entry.szExeFile.lower() == "spotify.exe":
                return True
            found = kernel32.Process32NextW(snap, ctypes.byref(entry))
        return False
    finally:
        kernel32.CloseHandle(snap)


def command_lines():
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name = 'Spotify.exe'\" | ForEach-Object { $_.CommandLine }",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in (completed.stdout or "").splitlines() if line.strip()]


def session_ids():
    try:
        return audio_session.spotify_pids()
    except OSError:
        return []


def set_muted(pid, muted):
    try:
        audio_session.set_pid_muted(pid, muted)
    except OSError:
        return


def release_mute():
    for pid in session_ids():
        set_muted(pid, False)


def press_next(client):
    note("next")
    if client is None:
        return
    client.next()


def apply_catch_up(watcher, uri):
    if isinstance(uri, str) and uri.startswith("spotify:ad:"):
        watcher.armed_uri = uri
        watcher.arm_at = time.time()
        watcher.muted = True
        watcher.mute_applied = True
        for pid in session_ids():
            set_muted(pid, True)
        note("catch " + uri)
        return
    if isinstance(uri, str) and uri.startswith("spotify:track:"):
        watcher.muted = False
        watcher.mute_applied = False
        watcher.armed_uri = None
        watcher.arm_at = None
        release_mute()
        note("catch " + uri)


def follow_log(still_running, path, client):
    watcher = Watcher()
    cursor = LogCursor()
    smtc = policy.SmtcCursor()
    log_seen = False
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        last = None
        while True:
            line = handle.readline()
            if not line:
                break
            uri = cursor.feed(line)
            if uri:
                last = uri
                log_seen = True
        if last:
            apply_catch_up(watcher, last)
        while still_running():
            line = handle.readline()
            if line:
                uri = cursor.feed(line)
                if uri:
                    log_seen = True
                    note(uri)
                    policy.react(
                        watcher,
                        uri,
                        time.time(),
                        time.sleep,
                        lambda: press_next(client),
                        set_muted,
                        session_ids,
                    )
                continue
            handle.seek(handle.tell())
            if not log_seen and client is not None:
                uri = smtc.feed(client.title())
                if uri:
                    note(uri)
                    policy.react(
                        watcher,
                        uri,
                        time.time(),
                        time.sleep,
                        lambda: press_next(client),
                        set_muted,
                        session_ids,
                    )
                    continue
            time.sleep(0.2)


def stop_spotify():
    subprocess.run(["taskkill", "/F", "/IM", "Spotify.exe"], check=False, capture_output=True)
    deadline = time.monotonic() + 8
    while spotify_running() and time.monotonic() < deadline:
        time.sleep(0.2)


def launch(path):
    truncate_log(Path(path))
    subprocess.Popen(build_argv(path))


def acquire_lock():
    import msvcrt

    path = log_path().with_name("watch.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+")
    try:
        handle.seek(0)
        if handle.read(1) == "":
            handle.write("1")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def run_session(path, client):
    if spotify_running() and not policy.main_has_log(command_lines(), path):
        stop_spotify()
        launch(path)
    elif not spotify_running():
        launch(path)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not spotify_running():
        time.sleep(0.2)
    if spotify_running():
        follow_log(spotify_running, path, client)


def ensure():
    lock = acquire_lock()
    if lock is None:
        return
    path = log_path()
    client = SmtcClient(Path(__file__).resolve().parent / "smtc_helper.ps1")
    try:
        while True:
            if not spotify_running():
                time.sleep(1.0)
                continue
            if not policy.main_has_log(command_lines(), path):
                stop_spotify()
                launch(path)
            follow_log(spotify_running, path, client)
            release_mute()
    finally:
        release_mute()
        client.close()


def main():
    path = log_path()
    client = SmtcClient(Path(__file__).resolve().parent / "smtc_helper.ps1")
    try:
        run_session(path, client)
    finally:
        release_mute()
        client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ensure":
        ensure()
    else:
        main()
