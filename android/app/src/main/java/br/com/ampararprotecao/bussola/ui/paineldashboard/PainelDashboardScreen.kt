package br.com.ampararprotecao.bussola.ui.paineldashboard

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.painelamparar.model.FaixaBoletos
import br.com.ampararprotecao.bussola.ui.components.formatBrl
import br.com.ampararprotecao.bussola.ui.components.formatNumber

@Composable
fun PainelDashboardScreen(modifier: Modifier = Modifier, viewModel: PainelDashboardViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    if (state.loading) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    val result = state.result
    LazyColumn(modifier = modifier.fillMaxSize().padding(16.dp)) {
        state.error?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }

        item {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Boletos a receber — ${result?.mesReferencia ?: "—"}", style = MaterialTheme.typography.labelMedium)
                    Text(formatBrl(result?.totalValor), style = MaterialTheme.typography.headlineMedium)
                    Text("${formatNumber(result?.totalQtd)} boletos em aberto no mês", style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        item {
            Row(
                Modifier.fillMaxWidth().padding(top = 16.dp, bottom = 8.dp),
                horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween,
            ) {
                Text("Por período", style = MaterialTheme.typography.titleMedium)
                Button(onClick = { viewModel.verificarAgora() }, enabled = !state.verifying) {
                    Text(if (state.verifying) "Verificando…" else "Verificar agora")
                }
            }
        }

        items(result?.faixas ?: emptyList()) { faixa: FaixaBoletos ->
            Row(
                Modifier.fillMaxWidth().padding(vertical = 8.dp),
                horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween,
            ) {
                Text(faixa.label)
                Column(horizontalAlignment = Alignment.End) {
                    Text(formatBrl(faixa.valor))
                    Text("${formatNumber(faixa.qtd)} boletos", style = MaterialTheme.typography.bodySmall)
                }
            }
            HorizontalDivider()
        }
    }
}
