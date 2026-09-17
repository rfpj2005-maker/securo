package br.com.ampararprotecao.bussola.ui.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.ui.SessionViewModel

/**
 * Only handles the TOTP branch — passkey-as-2FA is out of Fase 1 (see the
 * plan), so `methods` is shown only to explain what's available; a passkey-
 * only account without TOTP still hits a dead end here for now.
 */
@Composable
fun TwoFactorScreen(
    sessionViewModel: SessionViewModel,
    tempToken: String,
    methods: List<String>,
    onLoggedIn: () -> Unit,
    viewModel: LoginViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    var code by remember { mutableStateOf("") }

    LaunchedEffect(state) {
        if (state is LoginUiState.Success) {
            sessionViewModel.refreshWorkspaces()
            onLoggedIn()
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Verificação em duas etapas", style = MaterialTheme.typography.headlineSmall)
        Text("Digite o código do seu app autenticador", style = MaterialTheme.typography.bodyMedium)
        if (!methods.contains("totp")) {
            Text(
                "Sua conta usa passkey como segundo fator, que ainda não é suportado pelo app — use a versão web.",
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        Spacer(Modifier.padding(top = 24.dp))

        OutlinedTextField(
            value = code,
            onValueChange = { code = it; viewModel.resetError() },
            label = { Text("Código") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )

        if (state is LoginUiState.Error) {
            Text(
                (state as LoginUiState.Error).message,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        Spacer(Modifier.padding(top = 20.dp))

        Button(
            onClick = { viewModel.verifyTwoFactor(tempToken, code) },
            enabled = state !is LoginUiState.Loading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (state is LoginUiState.Loading) {
                CircularProgressIndicator(modifier = Modifier.padding(4.dp), color = MaterialTheme.colorScheme.onPrimary)
            } else {
                Text("Confirmar")
            }
        }
    }
}
