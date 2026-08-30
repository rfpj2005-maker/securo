package br.com.securo.wear.network

import br.com.securo.wear.data.ServerSettings
import br.com.securo.wear.data.TokenStore
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Builds a fresh Retrofit client bound to the current [ServerSettings.baseUrl].
 * Not a singleton on purpose: the base URL is user-editable (pairing
 * screen's "servidor" field), and Retrofit clients are cheap enough to
 * rebuild rather than plumb a mutable base URL through OkHttp.
 */
object ApiClient {
    private val json = Json { ignoreUnknownKeys = true }

    fun create(serverSettings: ServerSettings, tokenStore: TokenStore): SecuroApi {
        val logging = HttpLoggingInterceptor().apply {
            // BASIC, not BODY: a bearer token or task content in logcat
            // is not something a debug build should ship with checked in.
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .addInterceptor(AuthInterceptor(tokenStore))
            .addInterceptor(logging)
            .build()

        val baseUrl = serverSettings.baseUrl.let { if (it.endsWith("/")) it else "$it/" }

        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(SecuroApi::class.java)
    }
}
