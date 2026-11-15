package ru.stabilnoitochka.spotifyadmute

object AdBreak {
    fun isPlayerBreak(text: String): Boolean {
        val lower = text.lowercase()
        val label = "advertisement" in lower || "реклама" in lower || "объявление" in lower
        val timer = "left in the break" in lower || "в паузе" in lower || "перерыв" in lower
        return label && timer
    }

    fun isPlaybackNotice(text: String): Boolean {
        if (isPlayerBreak(text)) {
            return true
        }
        val lower = text.lowercase()
        val label = "advertisement" in lower || "реклама" in lower || "объявление" in lower
        return label && "•" in text
    }

    fun playingText(notice: String, session: String): String {
        if (session.isNotEmpty()) {
            return session
        }
        return notice
    }
}

enum class BreakAction {
    NONE,
    NEXT,
    MUTE,
    RESTORE,
}

class BreakVolume {
    private var remembered: Int? = null
    private var armAt: Long? = null

    fun onSample(isBreak: Boolean, nowMs: Long, currentVolume: Int): BreakAction {
        if (!isBreak) {
            armAt = null
            if (remembered != null) {
                return BreakAction.RESTORE
            }
            return BreakAction.NONE
        }
        val armed = armAt
        if (armed == null) {
            armAt = nowMs
            return BreakAction.NEXT
        }
        if (remembered == null && nowMs >= armed + 1000L) {
            remembered = currentVolume
            return BreakAction.MUTE
        }
        return BreakAction.NONE
    }

    fun takeRemembered(): Int? {
        val value = remembered
        remembered = null
        armAt = null
        return value
    }
}
