"""Pure decisions for the Windows watcher. No COM and no WinRT."""

AD_TITLES = ("advertisement", "реклама", "объявление")
MUTE_AGAIN = (0.1, 0.3)


def smtc_kind(title):
    if title is None:
        return None
    cleaned = title.strip().casefold()
    if not cleaned:
        return None
    if cleaned in AD_TITLES:
        return "ad"
    return "track"


class SmtcCursor:
    def __init__(self):
        self.mode = None
        self.generation = 0

    def feed(self, title):
        kind = smtc_kind(title)
        if kind is None:
            return None
        if kind != self.mode:
            self.generation += 1
            self.mode = kind
        if kind == "ad":
            return "spotify:ad:smtc:%d" % self.generation
        return "spotify:track:smtc:%d" % self.generation


def main_has_log(command_lines, log_path):
    needle = str(log_path)
    for line in command_lines:
        if "--type=" in line:
            continue
        if needle in line:
            return True
    return False


def is_spotify_image(path):
    if not path:
        return False
    folded = path.replace("/", "\\").casefold()
    return folded.endswith("\\spotify.exe")


def react(watcher, uri, now, sleep_fn, next_fn, set_muted, ids_fn):
    from spotify_ad_watch import Decision, decide_after, reapply_unmute

    muted = False
    for decision in decide_after(watcher, uri, now, sleep_fn, lambda current=uri: current):
        if decision is Decision.MUTE:
            for sink_id in ids_fn():
                set_muted(sink_id, True)
            muted = True
        elif decision is Decision.NEXT:
            next_fn()
        elif decision is Decision.UNMUTE:
            reapply_unmute(set_muted, ids_fn, sleep_fn)
    if not muted:
        return
    elapsed = 0.0
    for delay in MUTE_AGAIN:
        if delay > elapsed:
            sleep_fn(delay - elapsed)
            elapsed = delay
        for sink_id in ids_fn():
            set_muted(sink_id, True)
