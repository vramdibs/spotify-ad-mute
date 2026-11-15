package ru.stabilnoitochka.spotifyadmute

import android.accessibilityservice.AccessibilityService
import android.app.Notification
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class WindowPolicy {
    private val volume = BreakVolume()

    fun onWindowText(text: String, nowMs: Long, spotifyInFront: Boolean, currentVolume: Int): BreakAction {
        if (!spotifyInFront) {
            return BreakAction.NONE
        }
        return volume.onSample(AdBreak.isPlayerBreak(text), nowMs, currentVolume)
    }

    fun onPlaybackText(text: String, nowMs: Long, currentVolume: Int): BreakAction {
        return volume.onSample(AdBreak.isPlaybackNotice(text), nowMs, currentVolume)
    }

    fun apply(action: BreakAction, currentVolume: Int, writer: (Int) -> Unit) {
        if (action == BreakAction.MUTE) {
            writer(0)
            return
        }
        if (action == BreakAction.RESTORE) {
            val saved = volume.takeRemembered()
            if (saved != null) {
                writer(saved)
            }
        }
    }
}

class SpotifyAdService : AccessibilityService() {
    private var lastEventAt = -1_000L

    override fun onServiceConnected() {
        super.onServiceConnected()
        sampleActiveWindow()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null || event.packageName?.toString() != "com.spotify.music") {
            return
        }
        val now = event.eventTime
        if (now - lastEventAt < 500L) {
            return
        }
        lastEventAt = now
        if (event.eventType == AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED) {
            val text = notificationText(event)
            if (text.isNotEmpty()) {
                MuteController.onNotice(this, text)
            }
            return
        }
        sampleActiveWindow()
    }

    private fun sampleActiveWindow() {
        val root = rootInActiveWindow ?: return
        if (root.packageName?.toString() != "com.spotify.music") {
            return
        }
        val action = MuteController.onWindow(this, collectText(root))
        if (action == BreakAction.NEXT) {
            pressNext(root)
        }
    }

    private fun notificationText(event: AccessibilityEvent): String {
        val parts = ArrayList<String>()
        val lines = event.text
        if (lines != null) {
            for (line in lines) {
                val value = line?.toString()
                if (!value.isNullOrEmpty()) {
                    parts.add(value)
                }
            }
        }
        val notification = event.parcelableData as? Notification
        val extras = notification?.extras
        if (extras != null) {
            val keys = arrayOf(
                Notification.EXTRA_TITLE,
                Notification.EXTRA_TEXT,
                Notification.EXTRA_SUB_TEXT,
                Notification.EXTRA_BIG_TEXT
            )
            for (key in keys) {
                val value = extras.getCharSequence(key)?.toString()
                if (!value.isNullOrEmpty()) {
                    parts.add(value)
                }
            }
        }
        return parts.joinToString(" ")
    }

    override fun onInterrupt() {
        MuteController.restore(this)
    }

    override fun onDestroy() {
        MuteController.restore(this)
        super.onDestroy()
    }

    private fun pressNext(root: AccessibilityNodeInfo) {
        for (label in arrayOf("Next", "Далее", "Следующий")) {
            val nodes = root.findAccessibilityNodeInfosByText(label)
            if (nodes.isNotEmpty()) {
                nodes[0].performAction(AccessibilityNodeInfo.ACTION_CLICK)
                return
            }
        }
    }

    private fun collectText(node: AccessibilityNodeInfo): String {
        val parts = ArrayList<String>()
        appendText(node, parts)
        return parts.joinToString(" ")
    }

    private fun appendText(node: AccessibilityNodeInfo, parts: MutableList<String>) {
        val value = node.text?.toString()
        if (!value.isNullOrEmpty()) {
            parts.add(value)
        }
        for (index in 0 until node.childCount) {
            val child = node.getChild(index) ?: continue
            appendText(child, parts)
        }
    }
}
