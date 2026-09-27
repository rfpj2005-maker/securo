package br.com.ampararprotecao.bussola.ui.recurring

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.RECURRING_FREQUENCY_LABELS
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransaction

@Composable
fun RecurringListScreen(
    modifier: Modifier = Modifier,
    onAdd: () -> Unit,
    onOpen: (String) -> Unit,
    viewModel: RecurringViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        modifier = modifier,
        floatingActionButton = {
            FloatingActionButton(onClick = onAdd) { Icon(Icons.Filled.Add, contentDescription = "Nova recorrência") }
        },
    ) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            return@Scaffold
        }
        if (state.items.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Nenhuma transação recorrente", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            return@Scaffold
        }
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(bottom = 88.dp)) {
            items(state.items, key = { it.id }) { item ->
                RecurringRow(
                    item = item,
                    accountName = state.accountsById[item.accountId]?.let { it.displayName ?: it.name },
                    categoryName = state.categoriesById[item.categoryId]?.name,
                    onClick = { onOpen(item.id) },
                    onToggle = { viewModel.toggleActive(item) },
                )
                HorizontalDivider()
            }
        }
    }
}

@Composable
private fun RecurringRow(
    item: RecurringTransaction,
    accountName: String?,
    categoryName: String?,
    onClick: () -> Unit,
    onToggle: () -> Unit,
) {
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(item.description, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            val sign = if (item.type == "credit") "+" else "-"
            Text(
                "$sign R$ ${"%.2f".format(item.amount.toDoubleOrNull() ?: 0.0)} · ${RECURRING_FREQUENCY_LABELS[item.frequency] ?: item.frequency}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            val subtitle = listOfNotNull(accountName, categoryName).joinToString(" · ")
            if (subtitle.isNotBlank()) {
                Text(subtitle, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Switch(checked = item.isActive, onCheckedChange = { onToggle() })
    }
}
