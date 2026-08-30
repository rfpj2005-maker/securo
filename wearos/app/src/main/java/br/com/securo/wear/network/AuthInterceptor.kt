package br.com.securo.wear.network

import br.com.securo.wear.data.TokenStore
import okhttp3.Interceptor
import okhttp3.Response

/** Attaches the stored bearer token to every request. The
 *  watch-pair/redeem call itself is unauthenticated, so an absent token
 *  there is expected and fine — it just means that one request goes out
 *  with no Authorization header, same as any other unauthenticated call
 *  would. */
class AuthInterceptor(private val tokenStore: TokenStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = tokenStore.accessToken
        val request = chain.request().let { original ->
            if (token.isNullOrBlank()) {
                original
            } else {
                original.newBuilder()
                    .header("Authorization", "Bearer $token")
                    .build()
            }
        }
        return chain.proceed(request)
    }
}
