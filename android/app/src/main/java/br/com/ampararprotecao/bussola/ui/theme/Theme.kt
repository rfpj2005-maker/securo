package br.com.ampararprotecao.bussola.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

private val LightColors = lightColorScheme(primary = PrimaryLight, secondary = PrimaryLight)
private val DarkColors = darkColorScheme(primary = PrimaryDark, secondary = PrimaryDark)

@Composable
fun BussolaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color (Material You) would drift from the web app's fixed
    // brand indigo — off by default so the app stays visually consistent
    // with Bússola on the web.
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColors
        else -> LightColors
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content,
    )
}
