package ru.stabilnoitochka.spotifyadmute

import android.content.Context
import android.media.AudioManager
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log

object MuteController {
    private const val TAG = "SpotifyAdMute"
    private val policy = WindowPolicy()
    private val handler = Handler(Looper.getMainLooper())
    private var pendingText: String? = null
    private var pendingNotice = false
    private var appContext: Context? = null
    private var lastLogged = ""
    private val recheck = Runnable {
        val context = appContext ?: return@Runnable
        apply(context, pendingText, pendingNotice)
    }

    fun onNotice(context: Context, text: String) {
        if (text.isEmpty()) {
            Log.i(TAG, "notice empty")
            return
        }
        appContext = context.applicationContext
        pendingText = text
        pendingNotice = true
        apply(context, text, true)
    }

    fun onWindow(context: Context, text: String): BreakAction {
        appContext = context.applicationContext
        pendingText = text
        pendingNotice = false
        return apply(context, text, false)
    }

    fun restore(context: Context) {
        handler.removeCallbacks(recheck)
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val current = audio.getStreamVolume(AudioManager.STREAM_MUSIC)
        policy.apply(BreakAction.RESTORE, current) { level ->
            audio.setStreamVolume(AudioManager.STREAM_MUSIC, level, 0)
        }
    }

    private fun apply(context: Context, text: String?, fromNotice: Boolean): BreakAction {
        if (text.isNullOrEmpty()) {
            return BreakAction.NONE
        }
        val now = SystemClock.uptimeMillis()
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val current = audio.getStreamVolume(AudioManager.STREAM_MUSIC)
        val action = if (fromNotice) {
            policy.onPlaybackText(text, now, current)
        } else {
            policy.onWindowText(text, now, true, current)
        }
        val line = "notice=$fromNotice action=$action volume=$current text=${text.take(120)}"
        if (line != lastLogged) {
            lastLogged = line
            Log.i(TAG, line)
        }
        if (action == BreakAction.NEXT) {
            handler.postDelayed(recheck, 1000L)
        }
        if (action == BreakAction.RESTORE) {
            handler.removeCallbacks(recheck)
            pendingText = null
            pendingNotice = false
        }
        policy.apply(action, current) { level ->
            audio.setStreamVolume(AudioManager.STREAM_MUSIC, level, 0)
        }
        return action
    }
}
