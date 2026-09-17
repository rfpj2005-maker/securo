package br.com.ampararprotecao.bussola.ui.cobranca

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.painelamparar.model.NegativadoItem
import br.com.ampararprotecao.bussola.data.painelamparar.model.NegativadosStatus
import br.com.ampararprotecao.bussola.data.painelamparar.repository.PainelNegativadosRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

const val SITUACAO_EM_ATRASO = "Em Atraso"
const val SITUACAO_INADIMPLENTE = "Inadimplente"
const val SITUACAO_NEGATIVADO = "Negativado"
val SITUACOES = listOf(SITUACAO_EM_ATRASO, SITUACAO_INADIMPLENTE, SITUACAO_NEGATIVADO)

data class CobrancaUiState(
    val loading: Boolean = true,
    val items: List<NegativadoItem> = emptyList(),
    val status: NegativadosStatus? = null,
    val situacaoFiltro: String? = null,
    val error: String? = null,
)

@HiltViewModel
class CobrancaViewModel @Inject constructor(private val repository: PainelNegativadosRepository) : ViewModel() {

    private val _state = MutableStateFlow(CobrancaUiState())
    val state: StateFlow<CobrancaUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching {
                val items = repository.list()
                val status = repository.status()
                items to status
            }.onSuccess { (items, status) ->
                _state.value = _state.value.copy(loading = false, items = items, status = status)
            }.onFailure {
                _state.value = _state.value.copy(loading = false, error = it.message)
            }
        }
    }

    fun setSituacao(situacao: String?) {
        _state.value = _state.value.copy(situacaoFiltro = situacao)
    }
}
