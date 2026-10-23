package br.com.amparar.cameras

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.TextView
import androidx.annotation.OptIn
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.rtsp.RtspMediaSource
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView

/**
 * Um quadro do mosaico: um player RTSP com nome, aviso de status e
 * reconexão automática (2 s → 30 s) quando a câmera cai ou trava.
 */
@OptIn(UnstableApi::class)
@SuppressLint("ViewConstructor")
class CameraTile(
    context: Context,
    val camera: Camera,
    private val fullscreen: Boolean,
) : FrameLayout(context) {

    private val handler = Handler(Looper.getMainLooper())
    private var player: ExoPlayer? = null
    private var retryDelayMs = MIN_RETRY_MS
    private var bufferingSince = 0L

    private val playerView = PlayerView(context).apply {
        useController = false
        resizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT
        setShutterBackgroundColor(Color.BLACK)
        setKeepContentOnPlayerReset(true)
        isFocusable = false
    }

    private val label = TextView(context).apply {
        text = camera.name
        setTextColor(Color.WHITE)
        setTextSize(TypedValue.COMPLEX_UNIT_SP, if (fullscreen) 18f else 13f)
        setBackgroundColor(0x99000000.toInt())
        setPadding(dp(8), dp(2), dp(8), dp(2))
    }

    private val status = TextView(context).apply {
        setTextColor(0xFFFFD54F.toInt())
        setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
        gravity = Gravity.CENTER
    }

    private val retry = Runnable { start() }

    // Live travado em "carregando" por muito tempo também conta como queda.
    private val watchdog = object : Runnable {
        override fun run() {
            if (bufferingSince > 0 && SystemClock.elapsedRealtime() - bufferingSince > STALL_MS) {
                fail("Sem imagem — reconectando…")
            } else {
                handler.postDelayed(this, 5_000)
            }
        }
    }

    private val listener = object : Player.Listener {
        override fun onPlaybackStateChanged(state: Int) {
            when (state) {
                Player.STATE_READY -> {
                    bufferingSince = 0
                    retryDelayMs = MIN_RETRY_MS
                    status.visibility = View.GONE
                }
                Player.STATE_BUFFERING -> {
                    if (bufferingSince == 0L) bufferingSince = SystemClock.elapsedRealtime()
                }
                Player.STATE_ENDED -> fail("Transmissão encerrada — reconectando…")
                Player.STATE_IDLE -> Unit
            }
        }

        override fun onPlayerError(error: PlaybackException) {
            fail("Sem sinal — tentando de novo…")
        }
    }

    init {
        val pad = if (fullscreen) 0 else dp(3)
        setPadding(pad, pad, pad, pad)
        setBackgroundColor(Color.BLACK)
        isFocusable = !fullscreen
        setOnFocusChangeListener { _, hasFocus ->
            setBackgroundColor(if (hasFocus) 0xFF42A5F5.toInt() else Color.BLACK)
        }
        addView(playerView, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        addView(status, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        addView(label, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT, Gravity.BOTTOM or Gravity.START))
    }

    fun start() {
        releasePlayer()
        showStatus("Conectando…")
        val url = if (fullscreen) camera.url else camera.gridUrl
        val p = ExoPlayer.Builder(context)
            // Buffer curto: é ao vivo, atraso pequeno vale mais que suavidade.
            .setLoadControl(DefaultLoadControl.Builder().setBufferDurationsMs(500, 2_000, 250, 500).build())
            .build()
        // Câmera não precisa de áudio: desligar poupa decodificador e CPU.
        p.trackSelectionParameters = p.trackSelectionParameters.buildUpon()
            .setTrackTypeDisabled(C.TRACK_TYPE_AUDIO, true)
            .build()
        p.volume = 0f
        val source = RtspMediaSource.Factory()
            .setForceUseRtpTcp(camera.tcp)
            .setTimeoutMs(8_000)
            .createMediaSource(MediaItem.fromUri(url))
        p.addListener(listener)
        p.setMediaSource(source)
        p.playWhenReady = true
        p.prepare()
        playerView.player = p
        player = p
        bufferingSince = SystemClock.elapsedRealtime()
        handler.removeCallbacks(watchdog)
        handler.postDelayed(watchdog, 5_000)
    }

    fun release() {
        handler.removeCallbacksAndMessages(null)
        releasePlayer()
    }

    private fun fail(message: String) {
        showStatus(message)
        handler.removeCallbacksAndMessages(null)
        releasePlayer()
        handler.postDelayed(retry, retryDelayMs)
        retryDelayMs = (retryDelayMs * 2).coerceAtMost(MAX_RETRY_MS)
    }

    private fun releasePlayer() {
        bufferingSince = 0
        player?.let {
            it.removeListener(listener)
            it.release()
        }
        player = null
        playerView.player = null
    }

    private fun showStatus(message: String) {
        status.text = message
        status.visibility = View.VISIBLE
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    companion object {
        private const val MIN_RETRY_MS = 2_000L
        private const val MAX_RETRY_MS = 30_000L
        private const val STALL_MS = 20_000L
    }
}
