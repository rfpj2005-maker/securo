package br.com.ampararprotecao.bussola.ui.recurring

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
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.RECURRING_FREQUENCIES
import br.com.ampararprotecao.bussola.data.bussola.model.RECURRING_FREQUENCY_LABELS
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransactionCreate
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransactionUpdate

@Composable
fun RecurringEditScreen(
    modifier: Modifier = Modifier,
    recurringId: String?,
    onSaved: () -> Unit,
    onDeleted: () -> Unit,
    viewModel: RecurringEditViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(recurringId) { viewModel.load(recurringId) }

    when (val s = state) {
        is RecurringEditUiState.Loading -> Box(modifier.fillMaxSize(), contentAlignment = androidx.compose.ui.Alignment.Center) {
            CircularProgressIndicator()
        }
        is RecurringEditUiState.Saved -> LaunchedEffect(Unit) { onSaved() }
        is RecurringEditUiState.Deleted -> LaunchedEffect(Unit) { onDeleted() }
        is RecurringEditUiState.Ready -> RecurringEditForm(
            modifier = modifier,
            existing = s,
            recurringId = recurringId,
            onSave = { create, update -> viewModel.save(recurringId, create, update) },
            onDelete = { recurringId?.let { viewModel.delete(it) } },
        )
    }
}

@Composable
private fun RecurringEditForm(
    modifier: Modifier,
    existing: RecurringEditUiState.Ready,
    recurringId: String?,
    onSave: (RecurringTransactionCreate, RecurringTransactionUpdate) -> Unit,
    onDelete: () -> Unit,
) {
    val item = existing.item
    var description by remember { mutableStateOf(item?.description ?: "") }
    var amountText by remember { mutableStateOf(item?.amount ?: "") }
    var type by remember { mutableStateOf(item?.type ?: "debit") }
    var frequency by remember { mutableStateOf(item?.frequency ?: "monthly") }
    var startDate by remember { mutableStateOf(item?.startDate ?: "") }
    var endDate by remember { mutableStateOf(item?.endDate ?: "") }
    var selectedAccount by remember { mutableStateOf(existing.accounts.firstOrNull { it.id == item?.accountId }) }
    var selectedCategory by remember { mutableStateOf(existing.categories.firstOrNull { it.id == item?.categoryId }) }

    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
    ) {
        OutlinedTextField(value = description, onValueChange = { description = it }, label = { Text("Descrição") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = amountText,
            onValueChange = { amountText = it },
            label = { Text("Valor") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
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
            label = "Frequência",
            options = RECURRING_FREQUENCIES,
            optionLabel = { RECURRING_FREQUENCY_LABELS[it] ?: it },
            selected = frequency,
            onSelect = { frequency = it },
        )
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
        OutlinedTextField(value = startDate, onValueChange = { startDate = it }, label = { Text("Início (AAAA-MM-DD)") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(value = endDate, onValueChange = { endDate = it }, label = { Text("Fim (opcional)") }, modifier = Modifier.fillMaxWidth())

        existing.error?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp))
        }

        Spacer(Modifier.padding(top = 20.dp))
        Button(
            onClick = {
                val accountId = selectedAccount?.id ?: return@Button
                onSave(
                    RecurringTransactionCreate(
                        description = description,
                        amount = amountText,
                        type = type,
                        frequency = frequency,
                        startDate = startDate,
                        endDate = endDate.ifBlank { null },
                        accountId = accountId,
                        categoryId = selectedCategory?.id,
                    ),
                    RecurringTransactionUpdate(
                        description = description,
                        amount = amountText,
                        type = type,
                        frequency = frequency,
                        startDate = startDate,
                        endDate = endDate.ifBlank { null },
                        accountId = accountId,
                        categoryId = selectedCategory?.id,
                    ),
                )
            },
            enabled = !existing.saving && description.isNotBlank() && amountText.toDoubleOrNull() != null && selectedAccount != null && startDate.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (existing.saving) CircularProgressIndicator(Modifier.padding(4.dp), color = MaterialTheme.colorScheme.onPrimary)
            else Text("Salvar")
        }

        if (recurringId != null) {
            Spacer(Modifier.padding(top = 8.dp))
            OutlinedButton(onClick = onDelete, modifier = Modifier.fillMaxWidth()) { Text("Apagar") }
        }
    }
}

@Composable
private fun <T> Dropdown(label: String, options: List<T>, optionLabel: (T) -> String, selected: T?, onSelect: (T) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier = Modifier.fillMaxWidth()) {
        OutlinedTextField(
            value = selected?.let(optionLabel) ?: "",
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { Icon(Icons.Filled.ArrowDropDown, contentDescription = null) },
            modifier = Modifier.fillMaxWidth().clickable { expanded = true },
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(text = { Text(optionLabel(option)) }, onClick = { onSelect(option); expanded = false })
            }
        }
    }
}
