package br.com.ampararprotecao.bussola.di

import br.com.ampararprotecao.bussola.data.BussolaTokenStore
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaAccountsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaAuthApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCalendarApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCategoriesApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaDashboardApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaTasksApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaTransactionsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaWorkspacesApi
import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelAuthApi
import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelBoletosAReceberApi
import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelCarneApi
import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelNegativadosApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import java.util.concurrent.TimeUnit
import javax.inject.Qualifier
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

// 2026-09-22: this host moved from the personal Tailscale account to the
// company one (matrizamparar@) during the tailnet migration, which
// reassigned the hostname (old one, desktop-s200k6m.tail50b52d.ts.net, is
// dead now).
private const val BUSSOLA_BASE_URL = "https://servidor-ampara.tail887dc2.ts.net/api/"
private const val PAINEL_AMPARAR_BASE_URL = "https://servidor-ampara.tail887dc2.ts.net:8444/api/"

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class BussolaRetrofit

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class PainelAmpararRetrofit

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    @Provides
    @Singleton
    fun provideJson(): Json = json

    /** Bearer JWT + X-Workspace-Id on every request; clears the token store
     * (and, via its StateFlow, kicks the nav graph back to login) on 401. */
    @Provides
    @Singleton
    @BussolaRetrofit
    fun provideBussolaOkHttp(tokenStore: BussolaTokenStore): OkHttpClient {
        val authInterceptor = okhttp3.Interceptor { chain ->
            val builder = chain.request().newBuilder()
            tokenStore.accessToken?.let { builder.addHeader("Authorization", "Bearer $it") }
            tokenStore.workspaceId?.let { builder.addHeader("X-Workspace-Id", it) }
            val response = chain.proceed(builder.build())
            if (response.code == 401) tokenStore.clear()
            response
        }
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BASIC))
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    /** SSO (2026-09-16): Painel Amparar has no login of its own anymore —
     * it verifies the SAME Bússola Bearer JWT directly (shared secret),
     * so this client reuses the exact same token, just against a
     * different baseUrl. No cookie jar, no separate session. */
    @Provides
    @Singleton
    @PainelAmpararRetrofit
    fun providePainelAmpararOkHttp(tokenStore: BussolaTokenStore): OkHttpClient {
        val authInterceptor = okhttp3.Interceptor { chain ->
            val builder = chain.request().newBuilder()
            tokenStore.accessToken?.let { builder.addHeader("Authorization", "Bearer $it") }
            chain.proceed(builder.build())
        }
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BASIC))
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    @BussolaRetrofit
    fun provideBussolaRetrofit(@BussolaRetrofit client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BUSSOLA_BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides
    @Singleton
    @PainelAmpararRetrofit
    fun providePainelAmpararRetrofit(@PainelAmpararRetrofit client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(PAINEL_AMPARAR_BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides
    @Singleton
    fun provideBussolaAuthApi(@BussolaRetrofit retrofit: Retrofit): BussolaAuthApi = retrofit.create(BussolaAuthApi::class.java)

    @Provides
    @Singleton
    fun provideBussolaWorkspacesApi(@BussolaRetrofit retrofit: Retrofit): BussolaWorkspacesApi = retrofit.create(BussolaWorkspacesApi::class.java)

    @Provides
    @Singleton
    fun provideBussolaDashboardApi(@BussolaRetrofit retrofit: Retrofit): BussolaDashboardApi = retrofit.create(BussolaDashboardApi::class.java)

    @Provides
    @Singleton
    fun provideBussolaTransactionsApi(@BussolaRetrofit retrofit: Retrofit): BussolaTransactionsApi = retrofit.create(BussolaTransactionsApi::class.java)

    @Provides
    @Singleton
    fun provideBussolaCategoriesApi(@BussolaRetrofit retrofit: Retrofit): BussolaCategoriesApi = retrofit.create(BussolaCategoriesApi::class.java)

    @Provides
    @Singleton
    fun provideBussolaAccountsApi(@BussolaRetrofit retrofit: Retrofit): BussolaAccountsApi = retrofit.create(BussolaAccountsApi::class.java)

    @Provides
    @Singleton
    fun provideBussolaTasksApi(@BussolaRetrofit retrofit: Retrofit): BussolaTasksApi = retrofit.create(BussolaTasksApi::class.java)

    @Provides
    @Singleton
    fun provideBussolaCalendarApi(@BussolaRetrofit retrofit: Retrofit): BussolaCalendarApi = retrofit.create(BussolaCalendarApi::class.java)

    @Provides
    @Singleton
    fun providePainelAuthApi(@PainelAmpararRetrofit retrofit: Retrofit): PainelAuthApi = retrofit.create(PainelAuthApi::class.java)

    @Provides
    @Singleton
    fun providePainelCarneApi(@PainelAmpararRetrofit retrofit: Retrofit): PainelCarneApi = retrofit.create(PainelCarneApi::class.java)

    @Provides
    @Singleton
    fun providePainelNegativadosApi(@PainelAmpararRetrofit retrofit: Retrofit): PainelNegativadosApi = retrofit.create(PainelNegativadosApi::class.java)

    @Provides
    @Singleton
    fun providePainelBoletosAReceberApi(@PainelAmpararRetrofit retrofit: Retrofit): PainelBoletosAReceberApi = retrofit.create(PainelBoletosAReceberApi::class.java)
}
