import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spotify_ad_watch import (
    LOG_PATH,
    Decision,
    LogCursor,
    Watcher,
    apply_decision,
    build_spotify_argv,
    decide_after,
    first_mpris_uri,
    catch_up_lines,
    follow_lines,
    handle_uri,
    press_next,
    run_child,
    session_argv,
    spotify_sink_ids,
    truncate_log,
    uri_from_mpris_line,
    cmdline_has_log,
    ensure_action,
    flatpak_app_running,
)


def test_first_ad_uri_mutes_once():
    watcher = Watcher()
    assert watcher.on_uri("spotify:ad:a6de110d", now=0.0) is Decision.MUTE
    assert watcher.on_uri("spotify:ad:a6de110d", now=0.2) is Decision.NONE


def test_same_ad_uri_does_not_mute_again():
    watcher = Watcher()
    assert watcher.on_uri("spotify:ad:a6de110d", now=0.0) is Decision.MUTE
    assert watcher.on_uri("spotify:ad:a6de110d", now=1.0) is Decision.NONE


def test_track_after_mute_unmutes():
    watcher = Watcher()
    watcher.on_uri("spotify:ad:a6de110d", now=0.0)
    assert watcher.on_uri("spotify:track:12VRlypMnsX09G2iFGVSs5", now=30.0) is Decision.UNMUTE
    assert watcher.on_uri("spotify:track:12VRlypMnsX09G2iFGVSs5", now=31.0) is Decision.NONE


def test_second_ad_mutes_again():
    watcher = Watcher()
    watcher.on_uri("spotify:ad:a6de110d", now=0.0)
    assert watcher.on_uri("spotify:ad:f71e6526", now=28.0) is Decision.MUTE


def test_log_cursor_pairs_uri_with_ad_flag():
    cursor = LogCursor()
    assert cursor.feed("17:47:57.897 I track_uri: spotify:ad:a6de110d") is None
    assert cursor.feed("17:47:57.897 I ad: yes") == "spotify:ad:a6de110d"
    assert cursor.feed("17:48:53.967 I track_uri: spotify:track:12VRlypMnsX09G2iFGVSs5") is None
    assert cursor.feed("17:48:53.967 I ad: no") == "spotify:track:12VRlypMnsX09G2iFGVSs5"


def test_decide_after_mutes_then_skips_without_waiting():
    watcher = Watcher()
    slept = []

    def sleep_fn(seconds):
        slept.append(seconds)

    actions = decide_after(
        watcher,
        "spotify:ad:a6de110d",
        now=10.0,
        sleep_fn=sleep_fn,
        read_again_fn=lambda: "spotify:ad:a6de110d",
    )
    assert actions == [Decision.MUTE, Decision.NEXT]
    assert slept == []


def test_sink_ids_match_spotify_only():
    rows = [
        {"index": 7, "properties": {"application.name": "Firefox", "application.process.binary": "firefox"}},
        {"index": 9, "properties": {"application.name": "Spotify", "application.process.binary": "spotify"}},
    ]
    assert spotify_sink_ids(rows) == [9]


def test_argv_without_log_has_no_debug_flag():
    argv = build_spotify_argv(False, "/tmp/spotify-ad.log")
    assert argv == ["flatpak", "run", "com.spotify.Client"]


def test_argv_with_log_uses_debug_level_1():
    argv = build_spotify_argv(True, "/tmp/spotify-ad.log")
    assert argv == [
        "flatpak",
        "run",
        "com.spotify.Client",
        "--log-file=/tmp/spotify-ad.log",
        "--debug-level=1",
    ]


def test_truncate_log_makes_empty_file(tmp_path):
    path = tmp_path / "data" / "spotify-ad.log"
    path.parent.mkdir()
    path.write_text("old")
    truncate_log(path)
    assert path.read_text() == ""


def test_default_log_path_is_flatpak_data():
    assert str(LOG_PATH).endswith(".var/app/com.spotify.Client/data/spotify-ad.log")


def test_mpris_line_keeps_only_spotify_uri():
    assert uri_from_mpris_line("spotify:ad:a6de110d") == "spotify:ad:a6de110d"
    assert uri_from_mpris_line("spotify:track:12VRlypMnsX09G2iFGVSs5") == "spotify:track:12VRlypMnsX09G2iFGVSs5"
    assert uri_from_mpris_line("/com/spotify/track/4ztqlaGIZgiKzCRjHOn0NT") == "spotify:track:4ztqlaGIZgiKzCRjHOn0NT"
    assert uri_from_mpris_line("/com/spotify/ad/a6de110d") == "spotify:ad:a6de110d"
    assert uri_from_mpris_line("Advertisement") is None


def test_flatpak_ps_sees_spotify_instance():
    assert flatpak_app_running("com.spotify.Client\t120333\t4239102673\n") is True
    assert flatpak_app_running("") is False


def test_log_flag_is_required_for_an_already_open_player():
    assert cmdline_has_log(b"/app/extra/share/spotify/spotify --log-file=/tmp/spotify-ad.log --debug-level=1") is True
    assert cmdline_has_log(b"/app/extra/share/spotify/spotify") is False
    assert ensure_action(True, False, True) == "relaunch"
    assert ensure_action(True, True, True) == "follow"
    assert ensure_action(True, False, False) == "busy"


def test_apply_mute_sets_flag_true():
    calls = []
    apply_decision(
        Decision.MUTE,
        [9],
        set_muted=lambda sink_id, muted: calls.append((sink_id, muted)),
        next_fn=lambda: None,
    )
    assert calls == [(9, True)]


def test_apply_next_does_not_mute():
    calls = []
    sent = []
    apply_decision(
        Decision.NEXT,
        [9],
        set_muted=lambda sink_id, muted: calls.append((sink_id, muted)),
        next_fn=lambda: sent.append("next"),
    )
    assert calls == []
    assert sent == ["next"]


def test_apply_unmute_sets_flag_false():
    calls = []
    apply_decision(
        Decision.UNMUTE,
        [9],
        set_muted=lambda sink_id, muted: calls.append((sink_id, muted)),
        next_fn=lambda: None,
    )
    assert calls == [(9, False)]


def test_run_child_returns_when_process_exits_and_always_calls_on_exit():
    called = []
    code = run_child([sys.executable, "-c", "import sys; sys.exit(0)"], lambda: called.append("exit"))
    assert code == 0
    assert called == ["exit"]


def test_session_without_mpris_truncates_and_enables_log(tmp_path):
    log_path = tmp_path / "spotify-ad.log"
    log_path.write_text("stale")
    argv = session_argv(False, str(log_path))
    assert log_path.read_text() == ""
    assert "--debug-level=1" in argv


def test_session_with_mpris_uri_does_not_create_log(tmp_path):
    log_path = tmp_path / "spotify-ad.log"
    argv = session_argv(True, str(log_path))
    assert argv == ["flatpak", "run", "com.spotify.Client"]
    assert not log_path.exists()


def test_press_next_uses_mpris_method():
    calls = []
    press_next(runner=lambda argv, check: calls.append(argv))
    assert calls[0][-1] == "org.mpris.MediaPlayer2.Player.Next"


def test_follow_lines_mutes_ad_and_unmutes_track():
    muted = []
    follow_lines(
        [
            "spotify:ad:a6de110d",
            "spotify:ad:f71e6526",
            "spotify:track:12VRlypMnsX09G2iFGVSs5",
            "Advertisement",
        ],
        now_fn=lambda: 0.0,
        sleep_fn=lambda _seconds: None,
        next_fn=lambda: None,
        set_muted=lambda sink_id, flag: muted.append(flag),
        sink_ids_fn=lambda: [9],
    )
    assert muted[0] is True
    assert muted[-1] is False


def test_separate_uri_events_still_unmute():
    watcher = Watcher()
    muted = []
    for uri in (
        "spotify:ad:a6de110d",
        "spotify:ad:f71e6526",
        "spotify:track:12VRlypMnsX09G2iFGVSs5",
    ):
        handle_uri(
            watcher,
            uri,
            now=0.0,
            sleep_fn=lambda _seconds: None,
            next_fn=lambda: None,
            set_muted=lambda sink_id, flag: muted.append(flag),
            sink_ids_fn=lambda: [9],
        )
    assert muted == [True, True, False, False, False]


def test_unmute_reaches_sink_opened_later():
    watcher = Watcher()
    watcher.on_uri("spotify:ad:a6de110d", now=0.0)
    watcher.on_uri("spotify:ad:a6de110d", now=1.0)
    waves = iter([[4], [11], [11]])
    cleared = []
    handle_uri(
        watcher,
        "spotify:track:12VRlypMnsX09G2iFGVSs5",
        now=30.0,
        sleep_fn=lambda _seconds: None,
        next_fn=lambda: None,
        set_muted=lambda sink_id, flag: cleared.append((sink_id, flag)),
        sink_ids_fn=lambda: next(waves),
    )
    assert cleared[0] == (4, False)
    assert (11, False) in cleared


def test_catch_up_last_track_unmutes_without_replaying_ads():
    watcher = Watcher()
    muted = []
    sent = []
    catch_up_lines(
        [
            "track_uri: spotify:ad:a6de110d",
            "ad: yes",
            "track_uri: spotify:track:12VRlypMnsX09G2iFGVSs5",
            "ad: no",
        ],
        watcher,
        now=100.0,
        sleep_fn=lambda _seconds: None,
        next_fn=lambda: sent.append("next"),
        set_muted=lambda sink_id, flag: muted.append(flag),
        sink_ids_fn=lambda: [9],
    )
    assert sent == []
    assert muted == [False, False, False]
    assert watcher.muted is False


def test_catch_up_last_ad_mutes_without_next():
    watcher = Watcher()
    muted = []
    sent = []
    catch_up_lines(
        [
            "track_uri: spotify:ad:a6de110d",
            "ad: yes",
        ],
        watcher,
        now=100.0,
        sleep_fn=lambda _seconds: None,
        next_fn=lambda: sent.append("next"),
        set_muted=lambda sink_id, flag: muted.append(flag),
        sink_ids_fn=lambda: [9],
    )
    assert sent == []
    assert muted == [True]
    assert watcher.on_uri("spotify:ad:a6de110d", now=101.0) is Decision.NONE
    assert watcher.on_uri("spotify:track:12VRlypMnsX09G2iFGVSs5", now=102.0) is Decision.UNMUTE


def test_first_mpris_uri_returns_track():
    assert first_mpris_uri(["noise", "spotify:track:abc"], lambda: 0) == "spotify:track:abc"


def test_first_mpris_uri_none_after_deadline():
    assert first_mpris_uri(["noise"], lambda: 20) is None
