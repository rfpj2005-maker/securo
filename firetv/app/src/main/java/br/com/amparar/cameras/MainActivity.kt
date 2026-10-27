package br.com.amparar.cameras

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.ceil
import kotlin.math.sqrt

/**
 * Tela única do app: mosaico de câmeras por loja, tela cheia ao apertar OK.
 *
 * Controle remoto: ◀ ▶ nas bordas (ou ⏪ ⏩) troca de tela · OK amplia · Voltar retorna ·
 * ⏯ liga/desliga a troca automática · Menu (≡) configura a URL e recarrega a lista.
 */
class MainActivity : Activity() {

    private val handler = Handler(Looper.getMainLooper())
    private lateinit var root: FrameLayout
    private lateinit var mosaic: LinearLayout
    private lateinit var header: TextView

    private var config: CameraConfig? = null
    private var configSource = ""
    private var pageIndex = 0
    private var columns = 1
    private val tiles = mutableListOf<CameraTile>()
    private var fullscreenTile: CameraTile? = null
    private var visible = false
    private var lastInputAt = 0L
    private var lastBackAt = 0L
    private var loadGeneration = 0

    private val rotator = object : Runnable {
        override fun run() {
            val cfg = config ?: return
            if (!CameraConfig.autoRotate(this@MainActivity)) return
            val idle = SystemClock.elapsedRealtime() - lastInputAt > IDLE_BEFORE_ROTATE_MS
            if (fullscreenTile == null && idle && cfg.pages.size > 1) {
                showPage(pageIndex + 1)
            }
            handler.postDelayed(this, cfg.rotateSeconds * 1000L)
        }
    }

    private val clock = object : Runnable {
        override fun run() {
            updateHeader()
            handler.postDelayed(this, 30_000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        mosaic = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.BLACK)
        }
        header = TextView(this).apply {
            setTextColor(Color.WHITE)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            setBackgroundColor(0x99000000.toInt())
            setPadding(dp(10), dp(4), dp(10), dp(4))
        }
        root = FrameLayout(this).apply {
            setBackgroundColor(Color.BLACK)
            addView(mosaic, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
            addView(header, FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP or Gravity.END))
        }
        setContentView(root)
        hideSystemUi()
        applyIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (applyIntent(intent) && visible) loadConfig()
    }

    /** Permite configurar pelo adb: `am start -n br.com.amparar.cameras/.MainActivity --es configUrl http://...` */
    private fun applyIntent(intent: Intent?): Boolean {
        val url = intent?.getStringExtra("configUrl") ?: return false
        CameraConfig.setConfigUrl(this, url)
        return true
    }

    override fun onStart() {
        super.onStart()
        visible = true
        lastInputAt = SystemClock.elapsedRealtime()
        loadConfig()
        handler.post(clock)
    }

    override fun onStop() {
        super.onStop()
        // Fora da tela não decodifica nada: libera todos os players.
        visible = false
        handler.removeCallbacksAndMessages(null)
        releaseAll()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemUi()
    }

    private fun loadConfig() {
        val generation = ++loadGeneration
        if (config == null) header.text = "Carregando câmeras…"
        Thread {
            val result = runCatching { CameraConfig.load(applicationContext) }
            runOnUiThread {
                if (!visible || generation != loadGeneration) return@runOnUiThread
                result.onSuccess { (cfg, source) ->
                    config = cfg
                    configSource = source
                    restartRotator()
                    showPage(pageIndex)
                }.onFailure {
                    releaseAll()
                    header.text = "Lista de câmeras inválida — aperte Menu (≡)"
                }
            }
        }.start()
    }

    private fun restartRotator() {
        val cfg = config ?: return
        handler.removeCallbacks(rotator)
        if (CameraConfig.autoRotate(this)) handler.postDelayed(rotator, cfg.rotateSeconds * 1000L)
    }

    /** ⏯ liga/desliga a troca automática de tela; a escolha fica salva. */
    private fun toggleAutoRotate() {
        val on = !CameraConfig.autoRotate(this)
        CameraConfig.setAutoRotate(this, on)
        val seconds = config?.rotateSeconds ?: CameraConfig.DEFAULT_ROTATE_SECONDS
        // Ao ligar, a primeira troca acontece já no próximo intervalo.
        if (on) lastInputAt = 0
        restartRotator()
        updateHeader()
        val msg = if (on) "Troca automática LIGADA (a cada $seconds s)" else "Troca automática DESLIGADA"
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }

    private fun showPage(index: Int) {
        val pages = config?.pages.orEmpty()
        closeFullscreen(reopenGrid = false)
        releaseAll()
        if (pages.isEmpty()) {
            header.text = "Nenhuma câmera configurada — aperte Menu (≡)"
            return
        }
        pageIndex = index.mod(pages.size)
        val cams = pages[pageIndex].cameras
        columns = ceil(sqrt(cams.size.toDouble())).toInt()
        val rows = ceil(cams.size / columns.toDouble()).toInt()

        for (r in 0 until rows) {
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            for (c in 0 until columns) {
                val i = r * columns + c
                if (i < cams.size) {
                    val tile = CameraTile(this, cams[i], fullscreen = false)
                    tile.tag = i
                    tile.setOnClickListener { openFullscreen(i) }
                    tiles += tile
                    row.addView(tile, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f))
                } else {
                    row.addView(View(this), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f))
                }
            }
            mosaic.addView(row, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        }
        tiles.forEach { it.start() }
        tiles.firstOrNull()?.requestFocus()
        updateHeader()
    }

    private fun openFullscreen(index: Int) {
        val cams = config?.pages?.getOrNull(pageIndex)?.cameras ?: return
        if (cams.isEmpty()) return
        val i = index.mod(cams.size)
        // Solta o mosaico antes: o Fire TV tem poucos decodificadores de vídeo.
        releaseAll()
        fullscreenTile?.let { it.release(); root.removeView(it) }
        val tile = CameraTile(this, cams[i], fullscreen = true)
        tile.tag = i
        root.addView(tile, 1, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT))
        fullscreenTile = tile
        tile.start()
        updateHeader()
    }

    private fun closeFullscreen(reopenGrid: Boolean) {
        val tile = fullscreenTile ?: return
        tile.release()
        root.removeView(tile)
        fullscreenTile = null
        if (reopenGrid) showPage(pageIndex)
    }

    private fun releaseAll() {
        tiles.forEach { it.release() }
        tiles.clear()
        mosaic.removeAllViews()
    }

    private fun updateHeader() {
        val pages = config?.pages.orEmpty()
        if (pages.isEmpty()) return
        val time = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
        val title = fullscreenTile?.let { "${pages[pageIndex].title} · ${it.camera.name}" } ?: pages[pageIndex].title
        val auto = if (CameraConfig.autoRotate(this) && pages.size > 1) "   ⟳ auto" else ""
        header.text = "$title   ${pageIndex + 1}/${pages.size}$auto   $time"
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        lastInputAt = SystemClock.elapsedRealtime()
        val full = fullscreenTile
        when (keyCode) {
            KeyEvent.KEYCODE_MENU -> { showSettings(); return true }
            KeyEvent.KEYCODE_MEDIA_FAST_FORWARD, KeyEvent.KEYCODE_MEDIA_NEXT,
            KeyEvent.KEYCODE_CHANNEL_UP, KeyEvent.KEYCODE_PAGE_DOWN -> { showPage(pageIndex + 1); return true }
            KeyEvent.KEYCODE_MEDIA_REWIND, KeyEvent.KEYCODE_MEDIA_PREVIOUS,
            KeyEvent.KEYCODE_CHANNEL_DOWN, KeyEvent.KEYCODE_PAGE_UP -> { showPage(pageIndex - 1); return true }
            KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE, KeyEvent.KEYCODE_MEDIA_PLAY,
            KeyEvent.KEYCODE_MEDIA_PAUSE -> { toggleAutoRotate(); return true }
        }
        if (full != null) {
            when (keyCode) {
                KeyEvent.KEYCODE_BACK, KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER -> {
                    closeFullscreen(reopenGrid = true); return true
                }
                // Na tela cheia, ◀ ▶ passa para a câmera vizinha da mesma loja.
                KeyEvent.KEYCODE_DPAD_LEFT -> { openFullscreen((full.tag as Int) - 1); return true }
                KeyEvent.KEYCODE_DPAD_RIGHT -> { openFullscreen((full.tag as Int) + 1); return true }
            }
            return super.onKeyDown(keyCode, event)
        }
        val focused = (currentFocus as? CameraTile)?.tag as? Int
        when (keyCode) {
            KeyEvent.KEYCODE_DPAD_LEFT -> if (focused == null || focused % columns == 0) {
                showPage(pageIndex - 1); return true
            }
            KeyEvent.KEYCODE_DPAD_RIGHT -> if (focused == null || focused % columns == columns - 1 || focused == tiles.size - 1) {
                showPage(pageIndex + 1); return true
            }
            KeyEvent.KEYCODE_BACK -> {
                // Tela de monitoramento: Voltar só sai se apertado duas vezes.
                val now = SystemClock.elapsedRealtime()
                if (now - lastBackAt < 2_000) finish()
                else Toast.makeText(this, "Aperte Voltar de novo para sair", Toast.LENGTH_SHORT).show()
                lastBackAt = now
                return true
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    private fun showSettings() {
        val input = EditText(this).apply {
            setText(CameraConfig.configUrl(this@MainActivity))
            hint = "http://servidor:porta/cameras.json"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setSingleLine()
        }
        val version = packageManager.getPackageInfo(packageName, 0).versionName
        AlertDialog.Builder(this)
            .setTitle("Lista de câmeras (v$version · origem: $configSource)")
            .setMessage("URL do JSON com as câmeras. Vazio = lista embutida no app.")
            .setView(input)
            .setPositiveButton("Salvar e recarregar") { _, _ ->
                CameraConfig.setConfigUrl(this, input.text.toString())
                pageIndex = 0
                loadConfig()
            }
            .setNeutralButton("Recarregar") { _, _ -> loadConfig() }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    @Suppress("DEPRECATION")
    private fun hideSystemUi() {
        window.decorView.systemUiVisibility = (View.SYSTEM_UI_FLAG_FULLSCREEN
            or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            or View.SYSTEM_UI_FLAG_LAYOUT_STABLE)
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    companion object {
        // Depois de mexer no controle, espera um pouco antes de voltar a girar.
        private const val IDLE_BEFORE_ROTATE_MS = 20_000L
    }
}
