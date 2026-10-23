package br.com.amparar.cameras

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Abre o mosaico quando o Fire TV liga (e depois de uma atualização do app). */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val launch = Intent(context, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        try {
            context.startActivity(launch)
        } catch (_: Exception) {
            // Fire OS 7+ pode bloquear abertura em segundo plano; ver scripts/instalar.sh (appops).
        }
    }
}
