package br.com.ampararprotecao.bussola.ui.theme

import androidx.compose.ui.graphics.Color

// Mirrors frontend/src/index.css + the live admin-configured brand override
// (GET /api/admin/default-colors — currently #FF0000 for both light and
// dark, set via Configurações admin no site). theme-utils.ts on the web
// derives --accent/--muted from this at runtime via CSS color-mix(); the
// *Accent/*Muted values below are that same math (10%/6% of the brand color
// mixed into black for dark, 90%/94% into white for light) precomputed,
// since Compose has no color-mix() equivalent.
val PrimaryLight = Color(0xFFFF0000)
val PrimaryDark = Color(0xFFFF0000)

val BackgroundLight = Color(0xFFF8F9FB)
val BackgroundDark = Color(0xFF0C0D12)
val SurfaceLight = Color(0xFFFFFFFF)
val SurfaceDark = Color(0xFF16171F)
val OnSurfaceLight = Color(0xFF0F172A)
val OnSurfaceDark = Color(0xFFF0F0F5)
val OutlineLight = Color(0xFFE8ECF1)
val OutlineDark = Color(0xFF2A2D3A)
val OnSurfaceVariantLight = Color(0xFF64748B)
val OnSurfaceVariantDark = Color(0xFF8A8F9E)

// color-mix(primary, white 90%) / color-mix(primary, black 90%)
val AccentLight = Color(0xFFFFE5E5)
val AccentDark = Color(0xFF1A0000)
// color-mix(primary, black 20%) / color-mix(primary, white 20%)
val OnAccentLight = Color(0xFFCC0000)
val OnAccentDark = Color(0xFFFF3333)

val CritLight = Color(0xFFB03A2E)
val CritDark = Color(0xFFE0776B)
val WarnLight = Color(0xFF9A6412)
val WarnDark = Color(0xFFD7A24E)
val OkLight = Color(0xFF2E7D32)
val OkDark = Color(0xFF66BB6A)
