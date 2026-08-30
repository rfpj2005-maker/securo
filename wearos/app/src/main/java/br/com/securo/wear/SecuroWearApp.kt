package br.com.securo.wear

import android.app.Application
import br.com.securo.wear.data.ServerSettings
import br.com.securo.wear.data.TokenStore

/**
 * Manual "DI container" — deliberately not Hilt/Koin. Two singletons for
 * a four-screen app doesn't earn a framework; if this grows past Phase 1
 * (voice, chat, recording) and the wiring gets unwieldy, that's the
 * point to reconsider, not before.
 */
class SecuroWearApp : Application() {
    lateinit var tokenStore: TokenStore
        private set
    lateinit var serverSettings: ServerSettings
        private set

    override fun onCreate() {
        super.onCreate()
        tokenStore = TokenStore(this)
        serverSettings = ServerSettings(this)
    }
}
