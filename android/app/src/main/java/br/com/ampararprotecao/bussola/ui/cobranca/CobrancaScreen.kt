package br.com.ampararprotecao.bussola.ui.cobranca

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.painelamparar.model.NegativadoItem
import br.com.ampararprotecao.bussola.ui.components.formatBrl

@Composable
fun CobrancaScreen(modifier: Modifier = Modifier, viewModel: CobrancaViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    if (state.loading) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    Column(modifier.fillMaxSize()) {
        LazyRow(Modifier.padding(16.dp)) {
            items(SITUACOES) { situacao ->
                FilterChip(
                    selected = state.situacaoFiltro == situacao,
                    onClick = { viewModel.setSituacao(if (state.situacaoFiltro == situacao) null else situacao) },
                    label = { Text("$situacao (${state.status?.porSituacao?.get(situacao) ?: 0})") },
                    modifier = Modifier.padding(end = 8.dp),
                )
            }
        }

        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(16.dp)) }

        val filtered = state.items.filter { state.situacaoFiltro == null || it.situacaoAtual == state.situacaoFiltro }
        LazyColumn {
            items(filtered) { item -> NegativadoRow(item) }
        }
    }
}

@Composable
private fun NegativadoRow(item: NegativadoItem) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp)) {
        Text(item.nome, style = MaterialTheme.typography.bodyLarge)
        Text("${item.placa} · ${item.situacaoAtual}", style = MaterialTheme.typography.bodySmall)
        Text(formatBrl(item.valorEmAberto), style = MaterialTheme.typography.titleSmall)
    }
    HorizontalDivider()
}
