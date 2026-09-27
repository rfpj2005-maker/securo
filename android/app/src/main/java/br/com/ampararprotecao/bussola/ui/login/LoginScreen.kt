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
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.autofill.AutofillNode
import androidx.compose.ui.autofill.AutofillType
import androidx.compose.ui.layout.boundsInWindow
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalAutofill
import androidx.compose.ui.platform.LocalAutofillTree
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.ui.SessionViewModel

// Password managers (1Password included) hook into Android's Autofill
// Framework, not just "any text field" — without a field explicitly
// registered as Username/Password (via an AutofillNode + the `autofill`
// modifier below), the framework never tells them this screen has
// anything fillable, so the suggestion chip never appears. This is the
// pre-1.8 Compose API (BOM here is 2024.06.00 / Compose UI 1.6.x, before
// the newer semantics-based `contentType` autofill landed) — same idea,
// more boilerplate: register a node with its field's bounding box, and
// request/cancel autofill as that field gains/loses focus.
@OptIn(ExperimentalComposeUiApi::class)
@Composable
private fun autofillModifier(autofillTypes: List<AutofillType>, onFill: (String) -> Unit): Modifier {
    val autofill = LocalAutofill.current
    val autofillTree = LocalAutofillTree.current
    val node = remember { AutofillNode(autofillTypes = autofillTypes, onFill = onFill) }
    autofillTree += node
    return Modifier
        .onGloballyPositioned { node.boundingBox = it.boundsInWindow() }
        .onFocusChanged { focusState ->
            if (focusState.isFocused) autofill?.requestAutofillForNode(node) else autofill?.cancelAutofillForNode(node)
        }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalComposeUiApi::class)
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
            modifier = Modifier
                .fillMaxWidth()
                .then(autofillModifier(listOf(AutofillType.Username, AutofillType.EmailAddress)) { username = it }),
            singleLine = true,
        )
        androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it; viewModel.resetError() },
            label = { Text("Senha") },
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier
                .fillMaxWidth()
                .then(autofillModifier(listOf(AutofillType.Password)) { password = it }),
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
