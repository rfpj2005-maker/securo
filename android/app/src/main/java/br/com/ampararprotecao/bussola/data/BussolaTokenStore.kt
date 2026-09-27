package br.com.ampararprotecao.bussola.data

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

private const val PREFS_NAME = "bussola_auth"
private const val TAG = "BussolaTokenStore"

/**
 * Creates the encrypted prefs, falling back to a plain (unencrypted)
 * SharedPreferences if the device's AndroidKeyStore can't handle it.
 * EncryptedSharedPreferences has real-world failure modes on some Samsung/
 * OEM builds (keystore corruption after an OS update, provider quirks) —
 * without this fallback that failure happens inside the Hilt object graph
 * at app startup, which crashes MainActivity before any UI can render
 * (seen as "the app opens and immediately closes"). Losing encryption on
 * an affected device is far better than the app being entirely unusable;
 * a first attempt also clears any half-written encrypted file before
 * retrying once, since a corrupted keyset is the most common cause.
 */
private fun createPrefs(context: Context): SharedPreferences {
    fun buildEncrypted(): SharedPreferences = EncryptedSharedPreferences.create(
        context,
        PREFS_NAME,
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )
    return try {
        buildEncrypted()
    } catch (e: Exception) {
        Log.w(TAG, "EncryptedSharedPreferences failed, clearing and retrying once", e)
        try {
            context.deleteSharedPreferences(PREFS_NAME)
            buildEncrypted()
        } catch (e2: Exception) {
            Log.e(TAG, "EncryptedSharedPreferences unusable on this device, falling back to plain prefs", e2)
            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        }
    }
}

/**
 * Holds the Bússola JWT and the active workspace id, encrypted at rest.
 * Everything the Bússola OkHttp interceptor needs to stamp a request.
 * [loggedIn] is a hot [StateFlow] (not just a property) so the nav graph
 * can react immediately when the auth interceptor clears the token on a
 * 401 — no polling, no manual event bus.
 */
@Singleton
class BussolaTokenStore @Inject constructor(@ApplicationContext context: Context) {

    private val prefs = createPrefs(context)

    private val _loggedIn = MutableStateFlow(!prefs.getString(KEY_TOKEN, null).isNullOrBlank())
    val loggedIn: StateFlow<Boolean> = _loggedIn.asStateFlow()

    var accessToken: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) {
            prefs.edit().putString(KEY_TOKEN, value).apply()
            _loggedIn.value = !value.isNullOrBlank()
        }

    var workspaceId: String?
        get() = prefs.getString(KEY_WORKSPACE_ID, null)
        set(value) = prefs.edit().putString(KEY_WORKSPACE_ID, value).apply()

    var isSuperuser: Boolean
        get() = prefs.getBoolean(KEY_IS_SUPERUSER, false)
        set(value) = prefs.edit().putBoolean(KEY_IS_SUPERUSER, value).apply()

    val isLoggedIn: Boolean get() = !accessToken.isNullOrBlank()

    fun clear() {
        prefs.edit().clear().apply()
        _loggedIn.value = false
    }

    private companion object {
        const val KEY_TOKEN = "access_token"
        const val KEY_WORKSPACE_ID = "workspace_id"
        const val KEY_IS_SUPERUSER = "is_superuser"
    }
}
