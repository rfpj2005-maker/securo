package br.com.securo.wear.theme

import androidx.compose.runtime.Composable
import androidx.wear.compose.material.Colors
import androidx.wear.compose.material.MaterialTheme

// Placeholder palette — align with Securo's actual brand tokens
// (frontend's `--primary` etc.) once this is past the proof-of-concept
// stage.
private val SecuroColors = Colors(
    primary = androidx.compose.ui.graphics.Color(0xFF4F46E5),
    primaryVariant = androidx.compose.ui.graphics.Color(0xFF4338CA),
    background = androidx.compose.ui.graphics.Color(0xFF0B0B12),
    surface = androidx.compose.ui.graphics.Color(0xFF16161F),
    onPrimary = androidx.compose.ui.graphics.Color.White,
    onBackground = androidx.compose.ui.graphics.Color.White,
    onSurface = androidx.compose.ui.graphics.Color.White,
)

@Composable
fun SecuroWearTheme(content: @Composable () -> Unit) {
    MaterialTheme(colors = SecuroColors, content = content)
}
