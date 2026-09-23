package br.com.ampararprotecao.bussola.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.ui.components.formatBrl

@Composable
fun DashboardScreen(
    modifier: Modifier = Modifier,
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    if (state.loading) {
        Column(modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(Modifier.padding(top = 48.dp))
        }
        return
    }

    LazyColumn(modifier = modifier.fillMaxSize().padding(16.dp)) {
        state.error?.let { error ->
            item { Text(error, color = MaterialTheme.colorScheme.error) }
        }

        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Saldo total", style = MaterialTheme.typography.labelMedium)
                    Text(
                        formatBrl(state.summary?.totalBalancePrimary),
                        style = MaterialTheme.typography.headlineMedium,
                    )
                }
            }
        }

        item {
            Card(Modifier.fillMaxWidth().padding(top = 12.dp)) {
                Column(Modifier.padding(16.dp)) {
                    Text("Este mês", style = MaterialTheme.typography.labelMedium)
                    Text("Receitas: " + formatBrl(state.summary?.monthlyIncomePrimary))
                    Text("Despesas: " + formatBrl(state.summary?.monthlyExpensesPrimary))
                    val pending = state.summary?.pendingCategorization ?: 0
                    if (pending > 0) {
                        Text(
                            "$pending transações sem categoria",
                            color = MaterialTheme.colorScheme.tertiary,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                }
            }
        }

        if (state.spendingByCategory.isNotEmpty()) {
            item {
                Text(
                    "Gastos por categoria",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 20.dp, bottom = 8.dp),
                )
            }
            items(state.spendingByCategory.take(6)) { cat ->
                Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        val dotColor = runCatching {
                            Color(android.graphics.Color.parseColor(cat.categoryColor))
                        }.getOrDefault(Color.Gray)
                        Box(Modifier.size(10.dp).background(dotColor, CircleShape))
                        Spacer(Modifier.size(8.dp))
                        Text(cat.categoryName)
                    }
                    Text(formatBrl(cat.total), style = MaterialTheme.typography.bodyMedium)
                }
                HorizontalDivider()
            }
        }

        if (state.recentTransactions.isNotEmpty()) {
            item {
                Text(
                    "Últimas transações",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 20.dp, bottom = 8.dp),
                )
            }
            items(state.recentTransactions) { tx ->
                Column(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Text(tx.description)
                    Text(formatBrl(tx.amount), style = MaterialTheme.typography.bodyMedium)
                }
                HorizontalDivider()
            }
        }
    }
}
