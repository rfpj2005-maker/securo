package br.com.amparar.cameras

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

data class Camera(
    val name: String,
    val url: String,
    val gridUrl: String,
    val tcp: Boolean,
)

data class Store(val name: String, val cameras: List<Camera>)

/** Uma "página" do mosaico: até [CameraConfig.maxPerPage] câmeras de uma loja. */
data class Page(val title: String, val cameras: List<Camera>)

data class CameraConfig(
    val stores: List<Store>,
    val rotateSeconds: Int,
    val maxPerPage: Int,
) {
    val pages: List<Page> by lazy {
        stores.flatMap { store ->
            val chunks = store.cameras.chunked(maxPerPage)
            chunks.mapIndexed { i, cams ->
                val suffix = if (chunks.size > 1) " (${i + 1}/${chunks.size})" else ""
                Page(store.name + suffix, cams)
            }
        }
    }

    companion object {
        private const val PREFS = "cameras"
        private const val KEY_URL = "config_url"
        private const val CACHE_FILE = "cameras-cache.json"

        fun configUrl(context: Context): String =
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_URL, "") ?: ""

        fun setConfigUrl(context: Context, url: String) {
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_URL, url.trim()).apply()
        }

        /**
         * Ordem: URL remota (e guarda cópia) → última cópia baixada → lista embutida no APK.
         * Roda em thread de fundo (faz rede).
         */
        fun load(context: Context): Pair<CameraConfig, String> {
            val cache = File(context.filesDir, CACHE_FILE)
            val remote = configUrl(context)
            if (remote.isNotEmpty()) {
                try {
                    val text = fetch(remote)
                    val config = parse(text)
                    cache.writeText(text)
                    return config to "remota"
                } catch (_: Exception) {
                    // segue para o cache
                }
                if (cache.exists()) {
                    try {
                        return parse(cache.readText()) to "cache (servidor fora do ar)"
                    } catch (_: Exception) {
                    }
                }
            }
            val text = context.assets.open("cameras.json").bufferedReader().use { it.readText() }
            return parse(text) to "embutida"
        }

        private fun fetch(url: String): String {
            val conn = URL(url).openConnection() as HttpURLConnection
            conn.connectTimeout = 5000
            conn.readTimeout = 5000
            try {
                if (conn.responseCode !in 200..299) error("HTTP ${conn.responseCode}")
                return conn.inputStream.bufferedReader().use { it.readText() }
            } finally {
                conn.disconnect()
            }
        }

        fun parse(text: String): CameraConfig {
            val root = JSONObject(text)
            val storesJson = root.getJSONArray("stores")
            val stores = (0 until storesJson.length()).map { i ->
                val s = storesJson.getJSONObject(i)
                val camsJson = s.getJSONArray("cameras")
                val cams = (0 until camsJson.length()).map { j ->
                    val c = camsJson.getJSONObject(j)
                    val url = c.getString("url")
                    Camera(
                        name = c.optString("name", "Câmera ${j + 1}"),
                        url = url,
                        gridUrl = c.optString("gridUrl", "").ifEmpty { url },
                        tcp = c.optBoolean("tcp", false),
                    )
                }
                Store(s.optString("name", "Loja ${i + 1}"), cams)
            }.filter { it.cameras.isNotEmpty() }
            return CameraConfig(
                stores = stores,
                rotateSeconds = root.optInt("rotateSeconds", 0).coerceAtLeast(0),
                maxPerPage = root.optInt("maxPerPage", 4).coerceIn(1, 9),
            )
        }
    }
}
