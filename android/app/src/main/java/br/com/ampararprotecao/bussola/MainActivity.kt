package br.com.ampararprotecao.bussola

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import br.com.ampararprotecao.bussola.ui.navigation.BussolaNavHost
import br.com.ampararprotecao.bussola.ui.theme.BussolaTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            BussolaTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    BussolaNavHost()
                }
            }
        }
    }
}
