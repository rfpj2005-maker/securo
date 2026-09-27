package br.com.ampararprotecao.bussola.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

// 1:1 with frontend/src/index.css's --radius scale (base --radius: 0.625rem
// = 10dp at the browser's 16px root, sm/md/lg/xl/2xl derived by +/- a fixed
// px offset from that base) — mapped onto Material3's five shape roles so
// cards, dialogs, menus, chips and text fields pick up the same corner
// rounding as their shadcn/ui counterparts on web instead of M3's defaults.
val BussolaShapes = Shapes(
    extraSmall = RoundedCornerShape(6.dp), // --radius-sm
    small = RoundedCornerShape(8.dp), // --radius-md
    medium = RoundedCornerShape(10.dp), // --radius-lg (the CSS base --radius)
    large = RoundedCornerShape(14.dp), // --radius-xl
    extraLarge = RoundedCornerShape(18.dp), // --radius-2xl
)
