package ru.stabilnoitochka.spotifyadmute

import android.app.Notification
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSession
import android.os.Handler
import android.os.Looper
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

class SpotifyNoticeService : NotificationListenerService() {
    private var controller: MediaController? = null
    private val sessionCallback = object : MediaController.Callback() {
        override fun onMetadataChanged(metadata: MediaMetadata?) {
            val session = sessionText(metadata)
            if (session.isNotEmpty()) {
                MuteController.onNotice(this@SpotifyNoticeService, session)
            }
        }
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        val posted = activeNotifications
        Log.i(TAG, "listener connected count=${posted?.size ?: 0}")
        if (posted == null) {
            return
        }
        for (item in posted) {
            read(item)
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        read(sbn)
    }

    private fun read(sbn: StatusBarNotification?) {
        if (sbn == null || sbn.packageName != SPOTIFY) {
            return
        }
        val notice = noticeText(sbn.notification)
        val session = watchSession(sbn.notification)
        MuteController.onNotice(this, AdBreak.playingText(notice, session))
    }

    private fun watchSession(notification: Notification): String {
        val token = mediaToken(notification) ?: return ""
        val existing = controller
        if (existing == null || existing.sessionToken != token) {
            existing?.unregisterCallback(sessionCallback)
            val created = MediaController(this, token)
            created.registerCallback(sessionCallback, Handler(Looper.getMainLooper()))
            controller = created
        }
        return sessionText(controller?.metadata)
    }

    @Suppress("DEPRECATION")
    private fun mediaToken(notification: Notification): MediaSession.Token? {
        return notification.extras.getParcelable(Notification.EXTRA_MEDIA_SESSION)
    }

    private fun sessionText(metadata: MediaMetadata?): String {
        if (metadata == null) {
            return ""
        }
        val keys = arrayOf(
            MediaMetadata.METADATA_KEY_DISPLAY_TITLE,
            MediaMetadata.METADATA_KEY_DISPLAY_SUBTITLE,
            MediaMetadata.METADATA_KEY_DISPLAY_DESCRIPTION,
            MediaMetadata.METADATA_KEY_TITLE,
            MediaMetadata.METADATA_KEY_ARTIST,
            MediaMetadata.METADATA_KEY_ALBUM
        )
        val parts = ArrayList<String>()
        for (key in keys) {
            val value = metadata.getText(key)?.toString()
            if (!value.isNullOrEmpty() && value !in parts) {
                parts.add(value)
            }
        }
        return parts.joinToString(" ")
    }

    private fun noticeText(notification: Notification): String {
        val parts = ArrayList<String>()
        val ticker = notification.tickerText?.toString()
        if (!ticker.isNullOrEmpty()) {
            parts.add(ticker)
        }
        val extras = notification.extras
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
        return parts.joinToString(" ")
    }

    companion object {
        private const val TAG = "SpotifyAdMute"
        private const val SPOTIFY = "com.spotify.music"
    }
}
