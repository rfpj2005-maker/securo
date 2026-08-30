package br.com.securo.wear.watchface

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.view.SurfaceHolder
import androidx.wear.watchface.CanvasType
import androidx.wear.watchface.ComplicationSlotsManager
import androidx.wear.watchface.Renderer
import androidx.wear.watchface.WatchFace
import androidx.wear.watchface.WatchFaceService
import androidx.wear.watchface.WatchFaceType
import androidx.wear.watchface.WatchState
import androidx.wear.watchface.style.CurrentUserStyleRepository
import androidx.wear.watchface.style.UserStyleSchema
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

/**
 * Digital-only face: time (and date below it), Securo's placeholder
 * brand color, no complications — matches the "nothing beyond the
 * hours for now" scope from planning. Complication slots are the
 * obvious next step if that changes later (next task due, unread
 * count, etc.) — see ComplicationSlotsManager below for where they'd
 * be registered.
 *
 * NOTE for whoever builds this: androidx.wear.watchface's Renderer API
 * has shifted across versions (CanvasRenderer vs CanvasRenderer2 with a
 * SharedAssets type param). This targets 1.2.1's CanvasRenderer; if
 * Android Studio flags it as removed/deprecated for the resolved
 * version, the fix is switching to CanvasRenderer2 — the render() body
 * below doesn't need to change, only the class signature.
 */
class SecuroWatchFaceService : WatchFaceService() {

    override fun createUserStyleSchema(): UserStyleSchema = UserStyleSchema(emptyList())

    override fun createComplicationSlotsManager(
        currentUserStyleRepository: CurrentUserStyleRepository,
    ): ComplicationSlotsManager = ComplicationSlotsManager(emptyList(), currentUserStyleRepository)

    override suspend fun createWatchFace(
        surfaceHolder: SurfaceHolder,
        watchState: WatchState,
        complicationSlotsManager: ComplicationSlotsManager,
        currentUserStyleRepository: CurrentUserStyleRepository,
    ): WatchFace {
        val renderer = SecuroCanvasRenderer(surfaceHolder, currentUserStyleRepository, watchState)
        return WatchFace(WatchFaceType.DIGITAL, renderer)
    }
}

private class SecuroCanvasRenderer(
    surfaceHolder: SurfaceHolder,
    currentUserStyleRepository: CurrentUserStyleRepository,
    watchState: WatchState,
) : Renderer.CanvasRenderer(
    surfaceHolder,
    currentUserStyleRepository,
    watchState,
    CanvasType.HARDWARE,
    interactiveDrawModeUpdateDelayMillis = 1000L,
) {
    private val timeFormatter = DateTimeFormatter.ofPattern("HH:mm")
    private val dateFormatter = DateTimeFormatter.ofPattern("d MMM")

    private val timePaint = Paint().apply {
        color = Color.WHITE
        textSize = 56f
        isAntiAlias = true
        textAlign = Paint.Align.CENTER
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }
    private val datePaint = Paint().apply {
        color = Color.parseColor("#4F46E5") // Securo placeholder brand color — see app module's colors.xml
        textSize = 22f
        isAntiAlias = true
        textAlign = Paint.Align.CENTER
    }
    private val backgroundPaint = Paint().apply {
        color = Color.parseColor("#0B0B12")
    }

    override fun render(canvas: Canvas, bounds: Rect, zonedDateTime: ZonedDateTime) {
        canvas.drawRect(bounds, backgroundPaint)
        val centerX = bounds.exactCenterX()
        val centerY = bounds.exactCenterY()
        canvas.drawText(zonedDateTime.format(timeFormatter), centerX, centerY, timePaint)
        canvas.drawText(zonedDateTime.format(dateFormatter), centerX, centerY + 36f, datePaint)
    }

    override fun renderHighlightLayer(canvas: Canvas, bounds: Rect, zonedDateTime: ZonedDateTime) {
        // No editable elements (no complications, no user style options)
        // to highlight in the watch face editor — nothing to draw here.
    }
}
