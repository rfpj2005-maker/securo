package br.com.ampararprotecao.bussola.ui.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
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
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.ui.SessionViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(
    sessionViewModel: SessionViewModel,
    onNeedsTwoFactor: (tempToken: String, methods: List<String>) -> Unit,
    onLoggedIn: () -> Unit,
    viewModel: LoginViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    LaunchedEffect(state) {
        when (val s = state) {
            is LoginUiState.NeedsTwoFactor -> onNeedsTwoFactor(s.tempToken, s.methods)
            is LoginUiState.Success -> {
                sessionViewModel.refreshWorkspaces()
                onLoggedIn()
            }
            else -> {}
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Bússola", style = androidx.compose.material3.MaterialTheme.typography.headlineMedium)
        Text("Entrar", style = androidx.compose.material3.MaterialTheme.typography.bodyMedium)

        androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 24.dp))

        OutlinedTextField(
            value = username,
            onValueChange = { username = it; viewModel.resetError() },
            label = { Text("E-mail") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it; viewModel.resetError() },
            label = { Text("Senha") },
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )

        if (state is LoginUiState.Error) {
            Text(
                (state as LoginUiState.Error).message,
                color = androidx.compose.material3.MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 20.dp))

        Button(
            onClick = { viewModel.login(username, password) },
            enabled = state !is LoginUiState.Loading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (state is LoginUiState.Loading) {
                CircularProgressIndicator(modifier = Modifier.padding(4.dp), color = androidx.compose.material3.MaterialTheme.colorScheme.onPrimary)
            } else {
                Text("Entrar")
            }
        }
    }
}
