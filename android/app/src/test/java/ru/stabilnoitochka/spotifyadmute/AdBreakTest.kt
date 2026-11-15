package ru.stabilnoitochka.spotifyadmute

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AdBreakTest {
    @Test
    fun feedCardIsNotABreak() {
        assertFalse(AdBreak.isPlayerBreak("Advertisement Listen now Best Christmas Songs"))
    }

    @Test
    fun englishBreakNeedsLabelAndTimer() {
        assertTrue(AdBreak.isPlayerBreak("Advertisement 1 of 2 28 seconds left in the break"))
        assertFalse(AdBreak.isPlayerBreak("left in the break"))
    }

    @Test
    fun russianBreakNeedsLabelAndPause() {
        assertTrue(AdBreak.isPlayerBreak("Реклама осталось в паузе"))
        assertFalse(AdBreak.isPlayerBreak("Реклама"))
    }

    @Test
    fun russianAnnouncementUsesBreakWord() {
        assertTrue(
            AdBreak.isPlayerBreak(
                "Воспроизведение продолжится после перерыва Spotify Объявление • 1 из 2"
            )
        )
        assertFalse(AdBreak.isPlayerBreak("Объявление"))
        assertFalse(AdBreak.isPlayerBreak("Spotify Объявление • 1 из 2"))
        assertTrue(AdBreak.isPlaybackNotice("Spotify Объявление • 1 из 2"))
        assertFalse(AdBreak.isPlaybackNotice("Listen to music, ad-free."))
    }

    @Test
    fun nextThenMuteAfterOneSecondThenRestoreRemembered() {
        val volume = BreakVolume()
        assertEquals(BreakAction.NEXT, volume.onSample(true, 0, 7))
        assertEquals(BreakAction.NONE, volume.onSample(true, 500, 7))
        assertEquals(BreakAction.MUTE, volume.onSample(true, 1000, 7))
        assertEquals(BreakAction.NONE, volume.onSample(true, 1500, 0))
        assertEquals(BreakAction.RESTORE, volume.onSample(false, 2000, 3))
        assertEquals(7, volume.takeRemembered())
    }

    @Test
    fun unknownTextDoesNotTouchVolume() {
        val volume = BreakVolume()
        assertEquals(BreakAction.NONE, volume.onSample(false, 0, 4))
        assertEquals(null, volume.takeRemembered())
    }

    @Test
    fun backgroundWindowDoesNothing() {
        val policy = WindowPolicy()
        assertEquals(BreakAction.NONE, policy.onWindowText("Advertisement left in the break", 0, false, 5))
    }

    @Test
    fun sessionSongRestoresWhileNoticeStillSaysAd() {
        val notice = "Listen to music, ad-free. Spotify Реклама • Можно пропустить"
        val session = "Can't Get Enough Of Your Love Papik Frankie Lovecchio"
        assertTrue(AdBreak.isPlaybackNotice(notice))
        assertFalse(AdBreak.isPlaybackNotice(session))
        val policy = WindowPolicy()
        val ad = "Spotify Объявление • 1 из 2"
        assertEquals(BreakAction.NEXT, policy.onPlaybackText(ad, 0, 4))
        assertEquals(BreakAction.MUTE, policy.onPlaybackText(ad, 1000, 4))
        val playing = AdBreak.playingText(notice, session)
        assertEquals(BreakAction.RESTORE, policy.onPlaybackText(playing, 5000, 0))
    }

    @Test
    fun pausedNoticeCounterMutes() {
        val policy = WindowPolicy()
        val notice = "Spotify Объявление • 1 из 2"
        assertEquals(BreakAction.NEXT, policy.onPlaybackText(notice, 0, 6))
        assertEquals(BreakAction.MUTE, policy.onPlaybackText(notice, 1000, 6))
    }

    @Test
    fun playbackNoticeMutesWithoutTheSpotifyWindow() {
        val policy = WindowPolicy()
        val written = mutableListOf<Int>()
        val writer = { level: Int ->
            written.add(level)
            Unit
        }
        val ad = "Воспроизведение продолжится после перерыва Объявление • 1 из 2"
        assertEquals(BreakAction.NEXT, policy.onPlaybackText(ad, 0, 6))
        assertEquals(BreakAction.MUTE, policy.onPlaybackText(ad, 1000, 6))
        policy.apply(BreakAction.MUTE, 6, writer)
        assertFalse(AdBreak.isPlayerBreak("Acqua e Sale — Papik, Frankie Lovecchio"))
        assertEquals(BreakAction.NONE, WindowPolicy().onWindowText("Spotify Объявление • 1 из 2", 0, true, 6))
        assertEquals(BreakAction.RESTORE, policy.onPlaybackText("Acqua e Sale — Papik", 5000, 0))
        policy.apply(BreakAction.RESTORE, 0, writer)
        assertEquals(listOf(0, 6), written)
    }

    @Test
    fun breakMutesThenRestoresSavedLevel() {
        val policy = WindowPolicy()
        val written = mutableListOf<Int>()
        val writer = { level: Int ->
            written.add(level)
            Unit
        }
        assertEquals(BreakAction.NEXT, policy.onWindowText("Advertisement left in the break", 0, true, 5))
        policy.apply(BreakAction.NEXT, 5, writer)
        assertEquals(BreakAction.MUTE, policy.onWindowText("Advertisement left in the break", 1000, true, 5))
        policy.apply(BreakAction.MUTE, 5, writer)
        assertEquals(BreakAction.RESTORE, policy.onWindowText("playlist", 5000, true, 0))
        policy.apply(BreakAction.RESTORE, 0, writer)
        assertEquals(listOf(0, 5), written)
    }
}
