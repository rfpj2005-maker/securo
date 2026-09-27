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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val LightColors = lightColorScheme(
    primary = PrimaryLight,
    onPrimary = Color.White,
    primaryContainer = AccentLight,
    onPrimaryContainer = OnAccentLight,
    secondary = PrimaryLight,
    secondaryContainer = AccentLight,
    onSecondaryContainer = OnAccentLight,
    background = BackgroundLight,
    onBackground = OnSurfaceLight,
    surface = SurfaceLight,
    onSurface = OnSurfaceLight,
    surfaceVariant = AccentLight,
    onSurfaceVariant = OnSurfaceVariantLight,
    outline = OutlineLight,
    error = Color(0xFFF43F5E),
    onError = Color.White,
)
private val DarkColors = darkColorScheme(
    primary = PrimaryDark,
    onPrimary = Color.White,
    primaryContainer = AccentDark,
    onPrimaryContainer = OnAccentDark,
    secondary = PrimaryDark,
    secondaryContainer = AccentDark,
    onSecondaryContainer = OnAccentDark,
    background = BackgroundDark,
    onBackground = OnSurfaceDark,
    surface = SurfaceDark,
    onSurface = OnSurfaceDark,
    surfaceVariant = AccentDark,
    onSurfaceVariant = OnSurfaceVariantDark,
    outline = OutlineDark,
    error = Color(0xFFFB7185),
    onError = BackgroundDark,
)

@Composable
fun BussolaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color (Material You) would drift from the web app's fixed
    // brand color — off by default so the app stays visually consistent
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
        shapes = BussolaShapes,
        typography = BussolaTypography,
        content = content,
    )
}
