package br.com.securo.wear.pairing

import android.app.RemoteInput
import android.content.Context
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.CircularProgressIndicator
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import androidx.wear.input.RemoteInputIntentHelper
import androidx.wear.input.WearableExtender
import br.com.securo.wear.R
import br.com.securo.wear.SecuroWearApp

private const val REMOTE_INPUT_KEY = "pairing_code"

/** First screen when there's no stored token. Delegates digit entry to
 *  Wear OS's system RemoteInput flow (the same one Messages/Gmail use
 *  for replies) instead of a hand-built on-watch keyboard — it already
 *  supports voice dictation, handwriting, and the paired phone's
 *  keyboard, all of which are far more reliable than a custom picker for
 *  something as fiddly as six digits on a round screen. */
@Composable
fun PairingScreen(onPaired: () -> Unit) {
    val context = LocalContext.current
    val app = context.applicationContext as SecuroWearApp
    val viewModel: PairingViewModel = viewModel(
        factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                PairingViewModel(app.serverSettings, app.tokenStore) as T
        },
    )
    val state by viewModel.state.collectAsState()

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        val data = result.data ?: return@rememberLauncherForActivityResult
        val typed = RemoteInput.getResultsFromIntent(data)
            ?.getCharSequence(REMOTE_INPUT_KEY)
            ?.toString()
        if (!typed.isNullOrBlank()) viewModel.redeem(typed)
    }

    LaunchedEffect(state) {
        if (state is PairingUiState.Success) onPaired()
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(text = stringResource(R.string.pairing_title), textAlign = TextAlign.Center)
        Spacer(modifier = Modifier.padding(4.dp))
        Text(
            text = stringResource(R.string.pairing_hint),
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.caption2,
        )
        Spacer(modifier = Modifier.padding(8.dp))

        when (state) {
            PairingUiState.Loading -> CircularProgressIndicator()
            PairingUiState.Error -> {
                Text(
                    text = stringResource(R.string.pairing_error),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.caption2,
                )
                Spacer(modifier = Modifier.padding(4.dp))
                Button(onClick = {
                    viewModel.resetError()
                    launcher.launch(buildRemoteInputIntent(context))
                }) {
                    Text(stringResource(R.string.pairing_confirm))
                }
            }
            else -> {
                Button(onClick = { launcher.launch(buildRemoteInputIntent(context)) }) {
                    Text(stringResource(R.string.pairing_confirm))
                }
            }
        }
    }
}

private fun buildRemoteInputIntent(context: Context): Intent {
    val extender = WearableExtender().apply { setEmojisAllowed(false) }
    val remoteInput = RemoteInput.Builder(REMOTE_INPUT_KEY)
        .setLabel(context.getString(R.string.pairing_title))
        .extend(extender)
        .build()
    val intent = RemoteInputIntentHelper.createActionRemoteInputIntent()
    RemoteInputIntentHelper.putRemoteInputsExtra(intent, listOf(remoteInput))
    return intent
}
