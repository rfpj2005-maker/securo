package br.com.securo.wear.data

import android.content.Context
import br.com.securo.wear.BuildConfig

/**
 * The backend's base URL — not sensitive, so plain SharedPreferences is
 * fine here (unlike TokenStore). Pre-filled from BuildConfig so a fresh
 * install works against the same instance the web app uses without any
 * typing; still editable in case that ever changes or you point this
 * build at a different Securo instance.
 */
class ServerSettings(context: Context) {
    private val prefs = context.getSharedPreferences("securo_watch_settings", Context.MODE_PRIVATE)

    var baseUrl: String
        get() = prefs.getString(KEY_BASE_URL, null) ?: BuildConfig.DEFAULT_BASE_URL
        set(value) = prefs.edit().putString(KEY_BASE_URL, value.trimEnd('/')).apply()

    companion object {
        private const val KEY_BASE_URL = "base_url"
    }
}
