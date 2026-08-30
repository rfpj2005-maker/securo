package br.com.securo.wear

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import br.com.securo.wear.nav.SecuroNavHost
import br.com.securo.wear.theme.SecuroWearTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = applicationContext as SecuroWearApp
        setContent {
            SecuroWearTheme {
                SecuroNavHost(isPaired = app.tokenStore.isPaired)
            }
        }
    }
}
