package br.com.ampararprotecao.bussola

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.sp
import br.com.ampararprotecao.bussola.data.CrashLog
import br.com.ampararprotecao.bussola.ui.navigation.BussolaNavHost
import br.com.ampararprotecao.bussola.ui.theme.BussolaTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // No remote access to a real device's logcat — if the app crashed
        // last launch, show what happened so a screenshot of this dialog
        // is enough to diagnose it, instead of just "abre e fecha".
        val lastCrash = CrashLog.consumeLast(this)
        setContent {
            BussolaTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    BussolaNavHost()
                }
                if (lastCrash != null) {
                    var showCrash by remember { mutableStateOf(true) }
                    if (showCrash) {
                        AlertDialog(
                            onDismissRequest = { showCrash = false },
                            title = { Text("O app fechou sozinho da última vez") },
                            text = { Text(lastCrash, fontFamily = FontFamily.Monospace, fontSize = 11.sp) },
                            confirmButton = { TextButton(onClick = { showCrash = false }) { Text("OK") } },
                        )
                    }
                }
            }
        }
    }
}
