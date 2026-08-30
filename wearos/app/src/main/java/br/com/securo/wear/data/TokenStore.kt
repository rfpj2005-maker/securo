package br.com.securo.wear.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Holds the bearer token issued by /auth/watch-pair/redeem.
 *
 * Encrypted at rest (never plain SharedPreferences for this) — a lost
 * watch shouldn't hand out a working Securo session to whoever finds it.
 * There is no refresh flow: once this expires (24h, see the backend's
 * watch_pairing.py), [accessToken] goes null-effective and the app falls
 * back to the pairing screen. Re-pairing is the only way back in.
 */
class TokenStore(context: Context) {
    private val prefs: SharedPreferences by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "securo_watch_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    var accessToken: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_TOKEN, value).apply()

    fun clear() {
        prefs.edit().remove(KEY_TOKEN).apply()
    }

    val isPaired: Boolean
        get() = !accessToken.isNullOrBlank()

    companion object {
        private const val KEY_TOKEN = "access_token"
    }
}
