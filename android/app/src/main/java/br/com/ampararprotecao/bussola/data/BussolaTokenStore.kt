package br.com.ampararprotecao.bussola.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Holds the Bússola JWT and the active workspace id, encrypted at rest.
 * Everything the Bússola OkHttp interceptor needs to stamp a request.
 * [loggedIn] is a hot [StateFlow] (not just a property) so the nav graph
 * can react immediately when the auth interceptor clears the token on a
 * 401 — no polling, no manual event bus.
 */
@Singleton
class BussolaTokenStore @Inject constructor(@ApplicationContext context: Context) {

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "bussola_auth",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

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
