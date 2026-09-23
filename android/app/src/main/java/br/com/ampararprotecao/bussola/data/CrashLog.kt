package br.com.ampararprotecao.bussola.data

import android.content.Context
import android.util.Log
import java.io.File
import java.util.Date

private const val CRASH_FILE = "last_crash.txt"

/**
 * Persists the last uncaught exception to a plain file so it survives the
 * process dying, and surfaces it once on the next launch (MainActivity
 * calls [consumeLast]). There's no way to pull a real device's logcat
 * remotely — a screenshot of this dialog is the fastest way to actually
 * see why "the app opens and immediately closes" instead of guessing.
 */
object CrashLog {
    fun install(context: Context) {
        val appContext = context.applicationContext
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            try {
                File(appContext.filesDir, CRASH_FILE).writeText(
                    "${Date()}\n${Log.getStackTraceString(throwable)}"
                )
            } catch (_: Exception) {
                // Best-effort only — logging the crash must never itself throw.
            }
            previous?.uncaughtException(thread, throwable)
        }
    }

    /** Returns the last recorded crash text, deleting it so it only shows once. */
    fun consumeLast(context: Context): String? {
        val file = File(context.applicationContext.filesDir, CRASH_FILE)
        if (!file.exists()) return null
        return try {
            file.readText().also { file.delete() }
        } catch (_: Exception) {
            null
        }
    }
}
