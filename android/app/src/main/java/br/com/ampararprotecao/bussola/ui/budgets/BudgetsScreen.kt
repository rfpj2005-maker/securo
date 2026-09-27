package br.com.ampararprotecao.bussola.ui.budgets

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.BudgetVsActual
import java.time.format.DateTimeFormatter
import java.util.Locale

private val MONTH_FMT = DateTimeFormatter.ofPattern("MMMM 'de' yyyy", Locale("pt", "BR"))

@Composable
fun BudgetsScreen(modifier: Modifier = Modifier, viewModel: BudgetsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var editing by remember { mutableStateOf<BudgetVsActual?>(null) }

    Scaffold(modifier = modifier) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = { viewModel.changeMonth(-1) }) { Icon(Icons.Filled.ChevronLeft, contentDescription = "Mês anterior") }
                Text(
                    state.month.format(MONTH_FMT).replaceFirstChar { it.titlecase(Locale("pt", "BR")) },
                    style = MaterialTheme.typography.titleSmall,
                )
                IconButton(onClick = { viewModel.changeMonth(1) }) { Icon(Icons.Filled.ChevronRight, contentDescription = "Próximo mês") }
            }
            HorizontalDivider()

            if (state.loading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
                return@Column
            }

            if (state.items.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Nenhuma categoria com gasto nesse mês", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                return@Column
            }

            LazyColumn(contentPadding = PaddingValues(bottom = 24.dp)) {
                items(state.items, key = { it.categoryId }) { item ->
                    BudgetRow(item, onClick = { editing = item })
                    HorizontalDivider()
                }
            }
        }
    }

    editing?.let { item ->
        BudgetEditDialog(
            item = item,
            hasBudget = state.budgetIdByCategory.containsKey(item.categoryId),
            onDismiss = { editing = null },
            onSave = { amount, recurring -> viewModel.setBudget(item.categoryId, amount, recurring) { editing = null } },
            onClear = { viewModel.clearBudget(item.categoryId) { editing = null } },
        )
    }
}

@Composable
private fun BudgetRow(item: BudgetVsActual, onClick: () -> Unit) {
    val actual = item.actualAmount.toDoubleOrNull() ?: 0.0
    val budget = item.budgetAmount?.toDoubleOrNull()
    val pct = if (budget != null && budget > 0) (actual / budget).coerceIn(0.0, 1.5) else null
    val barColor = when {
        pct == null -> MaterialTheme.colorScheme.outline
        pct > 1.0 -> Color(0xFFFB7185)
        pct > 0.85 -> Color(0xFFFBBF24)
        else -> Color(0xFF34D399)
    }

    Column(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 10.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(item.categoryName, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text(
                if (budget != null) "R$ ${"%.2f".format(actual)} / R$ ${"%.2f".format(budget)}" else "R$ ${"%.2f".format(actual)} · sem orçamento",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Box(
            Modifier
                .padding(top = 6.dp)
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp))
                .background(MaterialTheme.colorScheme.surfaceVariant),
        ) {
            if (pct != null) {
                Box(
                    Modifier
                        .fillMaxWidth(pct.toFloat().coerceIn(0f, 1f))
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .background(barColor),
                )
            }
        }
    }
}

@Composable
private fun BudgetEditDialog(
    item: BudgetVsActual,
    hasBudget: Boolean,
    onDismiss: () -> Unit,
    onSave: (amount: String, recurring: Boolean) -> Unit,
    onClear: () -> Unit,
) {
    var amount by remember { mutableStateOf(item.budgetAmount ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(item.categoryName) },
        text = {
            Column {
                OutlinedTextField(
                    value = amount,
                    onValueChange = { amount = it },
                    label = { Text("Orçamento do mês (R$)") },
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth(),
                )
                if (hasBudget) {
                    TextButton(onClick = onClear, modifier = Modifier.padding(top = 8.dp)) {
                        Text("Remover orçamento", color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { onSave(amount, false) }, enabled = amount.toDoubleOrNull() != null) { Text("Salvar") }
        },
        dismissButton = { OutlinedButton(onClick = onDismiss) { Text("Cancelar") } },
    )
}
