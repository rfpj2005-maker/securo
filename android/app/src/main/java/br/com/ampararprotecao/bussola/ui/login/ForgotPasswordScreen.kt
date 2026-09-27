package br.com.ampararprotecao.bussola.ui.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Explore
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@Composable
fun ForgotPasswordScreen(modifier: Modifier = Modifier, onBackToLogin: () -> Unit, viewModel: LoginViewModel = hiltViewModel()) {
    var email by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    var sent by remember { mutableStateOf(false) }

    Box(modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        Card(shape = MaterialTheme.shapes.large) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 32.dp, vertical = 32.dp)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                    Box(
                        Modifier
                            .size(44.dp)
                            .background(MaterialTheme.colorScheme.primaryContainer, RoundedCornerShape(14.dp)),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Filled.Explore, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    }
                    androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 12.dp))
                    Text("Esqueceu a senha?", style = MaterialTheme.typography.titleLarge)
                    Text(
                        if (sent) "Verifique seu e-mail pra continuar." else "Enviamos um link de redefinição pro seu e-mail.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }

                androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 20.dp))

                if (!sent) {
                    OutlinedTextField(
                        value = email,
                        onValueChange = { email = it },
                        label = { Text("E-mail") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 16.dp))
                    Button(
                        onClick = {
                            sending = true
                            viewModel.forgotPassword(email) { sending = false; sent = true }
                        },
                        enabled = !sending && email.isNotBlank(),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        if (sending) CircularProgressIndicator(Modifier.padding(4.dp), color = MaterialTheme.colorScheme.onPrimary)
                        else Text("Enviar link")
                    }
                }

                androidx.compose.foundation.layout.Spacer(Modifier.padding(top = 16.dp))
                Row(horizontalArrangement = Arrangement.Center, modifier = Modifier.fillMaxWidth()) {
                    androidx.compose.material3.TextButton(onClick = onBackToLogin) { Text("Voltar pro login") }
                }
            }
        }
    }
}
