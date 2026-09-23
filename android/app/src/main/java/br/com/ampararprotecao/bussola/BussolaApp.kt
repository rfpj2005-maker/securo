package br.com.ampararprotecao.bussola

import android.app.Application
import br.com.ampararprotecao.bussola.data.CrashLog
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class BussolaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        CrashLog.install(this)
    }
}
