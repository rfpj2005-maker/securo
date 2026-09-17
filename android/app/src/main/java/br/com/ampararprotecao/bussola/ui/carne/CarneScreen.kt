package br.com.ampararprotecao.bussola.ui.carne

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
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
import br.com.ampararprotecao.bussola.data.painelamparar.model.CarneItem
import br.com.ampararprotecao.bussola.ui.components.formatNumber

@Composable
fun CarneScreen(modifier: Modifier = Modifier, viewModel: CarneViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    if (state.loading) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    Column(modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween,
        ) {
            Column {
                Text("${formatNumber(state.items.size)} com carnê ativo", style = MaterialTheme.typography.titleMedium)
                Text(
                    "${formatNumber(state.items.count { it.precisaRenovarEmBreve })} renovando em até 30 dias",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Button(onClick = { viewModel.verificarAgora() }, enabled = !state.verifying) {
                Text(if (state.verifying) "Verificando…" else "Verificar agora")
            }
        }

        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(16.dp)) }

        LazyColumn {
            items(state.items) { item -> CarneRow(item) }
        }
    }
}

@Composable
private fun CarneRow(item: CarneItem) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp)) {
        Text(item.nome, style = MaterialTheme.typography.bodyLarge)
        Text("${item.placa} · coberto até ${item.cobertoAte}", style = MaterialTheme.typography.bodySmall)
        Text(
            "${item.diasRestantes}d restantes",
            color = when {
                item.diasRestantes <= 7 -> MaterialTheme.colorScheme.error
                item.precisaRenovarEmBreve -> MaterialTheme.colorScheme.tertiary
                else -> MaterialTheme.colorScheme.onSurface
            },
        )
    }
    HorizontalDivider()
}
