package br.com.ampararprotecao.bussola.ui.transactions

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.TransactionEditPayload

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransactionEditScreen(
    modifier: Modifier = Modifier,
    transactionId: String?,
    onSaved: () -> Unit,
    onDelete: (String) -> Unit,
    viewModel: TransactionEditViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(transactionId) { viewModel.load(transactionId) }

    when (val s = state) {
        is TransactionEditUiState.Loading -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is TransactionEditUiState.Saved -> LaunchedEffect(Unit) { onSaved() }
        is TransactionEditUiState.Ready -> TransactionEditForm(
            modifier = modifier,
            existing = s,
            transactionId = transactionId,
            onSave = { payload -> viewModel.save(transactionId, payload) },
            onDelete = onDelete,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TransactionEditForm(
    modifier: Modifier,
    existing: TransactionEditUiState.Ready,
    transactionId: String?,
    onSave: (TransactionEditPayload) -> Unit,
    onDelete: (String) -> Unit,
) {
    val tx = existing.transaction
    var description by remember { mutableStateOf(tx?.description ?: "") }
    var amountText by remember { mutableStateOf(tx?.amount?.toString() ?: "") }
    var date by remember { mutableStateOf(tx?.date ?: "") }
    var type by remember { mutableStateOf(tx?.type ?: "debit") }
    var notes by remember { mutableStateOf(tx?.notes ?: "") }
    var selectedAccount by remember { mutableStateOf(existing.accounts.firstOrNull { it.id == tx?.accountId }) }
    var selectedCategory by remember { mutableStateOf(existing.categories.firstOrNull { it.id == tx?.categoryId }) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        OutlinedTextField(
            value = description,
            onValueChange = { description = it },
            label = { Text("Descrição") },
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = amountText,
            onValueChange = { amountText = it },
            label = { Text("Valor") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = date,
            onValueChange = { date = it },
            label = { Text("Data (AAAA-MM-DD)") },
            modifier = Modifier.fillMaxWidth(),
        )

        Spacer(Modifier.padding(top = 12.dp))
        Row {
            FilterChip(selected = type == "debit", onClick = { type = "debit" }, label = { Text("Despesa") })
            Spacer(Modifier.padding(start = 8.dp))
            FilterChip(selected = type == "credit", onClick = { type = "credit" }, label = { Text("Receita") })
        }

        Spacer(Modifier.padding(top = 12.dp))
        Dropdown(
            label = "Conta",
            options = existing.accounts,
            optionLabel = { it.displayName ?: it.name },
            selected = selectedAccount,
            onSelect = { selectedAccount = it },
        )

        Spacer(Modifier.padding(top = 12.dp))
        Dropdown(
            label = "Categoria",
            options = existing.categories,
            optionLabel = { it.name },
            selected = selectedCategory,
            onSelect = { selectedCategory = it },
        )

        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = notes,
            onValueChange = { notes = it },
            label = { Text("Notas") },
            modifier = Modifier.fillMaxWidth(),
        )

        existing.error?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp))
        }

        Spacer(Modifier.padding(top = 20.dp))
        Button(
            onClick = {
                onSave(
                    TransactionEditPayload(
                        description = description,
                        amount = amountText.replace(",", ".").toDoubleOrNull(),
                        date = date.ifBlank { null },
                        type = type,
                        accountId = selectedAccount?.id,
                        categoryId = selectedCategory?.id,
                        notes = notes.ifBlank { null },
                    ),
                )
            },
            enabled = !existing.saving && description.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (existing.saving) CircularProgressIndicator(Modifier.padding(4.dp), color = MaterialTheme.colorScheme.onPrimary)
            else Text("Salvar")
        }

        if (transactionId != null) {
            Spacer(Modifier.padding(top = 8.dp))
            OutlinedButton(onClick = { onDelete(transactionId) }, modifier = Modifier.fillMaxWidth()) {
                Text("Apagar")
            }
        }
    }
}

/** Plain `Box` + `DropdownMenu` instead of Material3's ExposedDropdownMenuBox
 * — simpler, fewer moving parts, and its API has churned across Compose
 * BOM versions. Tapping the field opens a standard dropdown list. */
@Composable
private fun <T> Dropdown(
    label: String,
    options: List<T>,
    optionLabel: (T) -> String,
    selected: T?,
    onSelect: (T) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier = Modifier.fillMaxWidth()) {
        OutlinedTextField(
            value = selected?.let(optionLabel) ?: "",
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { Icon(Icons.Filled.ArrowDropDown, contentDescription = null) },
            modifier = Modifier
                .fillMaxWidth()
                .clickable { expanded = true },
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(optionLabel(option)) },
                    onClick = { onSelect(option); expanded = false },
                )
            }
        }
    }
}
