import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pc"))

from policy import SmtcCursor, is_spotify_image, main_has_log, react, smtc_kind
from spotify_ad_watch import Watcher


def test_smtc_title_allow_list_is_exact():
    assert smtc_kind("Advertisement") == "ad"
    assert smtc_kind("  реклама ") == "ad"
    assert smtc_kind("Объявление") == "ad"
    assert smtc_kind("Advertisement - Brand") == "track"
    assert smtc_kind("Spotify") == "track"
    assert smtc_kind("") is None
    assert smtc_kind(None) is None


def test_smtc_cursor_changes_uri_when_the_break_returns():
    cursor = SmtcCursor()
    first = cursor.feed("Advertisement")
    assert first == "spotify:ad:smtc:1"
    assert cursor.feed("Advertisement") == first
    track = cursor.feed("Artist - Song")
    assert track == "spotify:track:smtc:2"
    second = cursor.feed("Реклама")
    assert second == "spotify:ad:smtc:3"
    assert second != first


def test_main_process_log_ignores_helper_handles():
    log_path = r"C:\Users\tez\AppData\Local\spotify-ad-mute\spotify-ad.log"
    lines = [
        r'"C:\Users\tez\AppData\Roaming\Spotify\Spotify.exe" --type=utility --log-file=2992',
        r'"C:\Users\tez\AppData\Roaming\Spotify\Spotify.exe" --log-file=%s --debug-level=8' % log_path,
    ]
    assert main_has_log(lines, log_path) is True
    assert main_has_log(lines[:1], log_path) is False


def test_spotify_image_matches_exe_only():
    assert is_spotify_image(r"C:\Users\tez\AppData\Roaming\Spotify\Spotify.exe")
    assert is_spotify_image(r"C:\Users\tez\AppData\Roaming\Spotify\SpotifyLauncher.exe") is False


def test_react_mutes_before_next_and_mutes_again():
    events = []

    def set_muted(sink_id, muted):
        events.append(("set", sink_id, muted))

    def next_fn():
        events.append(("next",))

    def sleep_fn(seconds):
        events.append(("sleep", seconds))

    react(Watcher(), "spotify:ad:abc", 0.0, sleep_fn, next_fn, set_muted, lambda: [4])
    assert events[0] == ("set", 4, True)
    assert events[1] == ("next",)
    assert ("sleep", 0.1) in events
    assert events[-1] == ("set", 4, True)


def test_react_restores_after_a_track():
    events = []
    watcher = Watcher()

    def set_muted(sink_id, muted):
        events.append(("set", sink_id, muted))

    react(watcher, "spotify:ad:abc", 0.0, lambda seconds: None, lambda: None, set_muted, lambda: [4])
    events.clear()
    react(
        watcher,
        "spotify:track:abc",
        30.0,
        lambda seconds: events.append(("sleep", seconds)),
        lambda: None,
        set_muted,
        lambda: [4],
    )
    assert events[0] == ("set", 4, False)
    assert ("sleep", 0.3) in events
    assert events[-1] == ("set", 4, False)
