package br.com.ampararprotecao.bussola.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.em

// Web (index.css) sets h1/h2/h3 to `letter-spacing: -0.035em` and leans on
// Geist's 600/700/800 weights for headers — Geist itself isn't bundled here
// (no bundled font asset yet), but the weight + tracking is what actually
// reads as "web's bolder, tighter headers" at a glance, so those are worth
// matching even on the system font. Only the roles this app's screens
// actually use (titleLarge/Medium/Small for AppBar/section headers,
// headlineSmall for a couple of big numbers) are overridden — everything
// else stays Material3 default.
private val TightHeader = (-0.035).em

val BussolaTypography = Typography().let { base ->
    base.copy(
        headlineSmall = base.headlineSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = TightHeader),
        headlineMedium = base.headlineMedium.copy(fontWeight = FontWeight.Bold, letterSpacing = TightHeader),
        titleLarge = base.titleLarge.copy(fontWeight = FontWeight.SemiBold, letterSpacing = TightHeader),
        titleMedium = base.titleMedium.copy(fontWeight = FontWeight.SemiBold),
        titleSmall = base.titleSmall.copy(fontWeight = FontWeight.SemiBold),
    )
}
