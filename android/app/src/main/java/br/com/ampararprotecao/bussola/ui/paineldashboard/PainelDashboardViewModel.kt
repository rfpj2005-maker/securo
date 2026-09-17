package br.com.ampararprotecao.bussola.ui.paineldashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.painelamparar.model.BoletosAReceberResult
import br.com.ampararprotecao.bussola.data.painelamparar.repository.PainelBoletosAReceberRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PainelDashboardUiState(
    val loading: Boolean = true,
    val result: BoletosAReceberResult? = null,
    val verifying: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class PainelDashboardViewModel @Inject constructor(
    private val repository: PainelBoletosAReceberRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(PainelDashboardUiState())
    val state: StateFlow<PainelDashboardUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repository.result() }
                .onSuccess { _state.value = _state.value.copy(loading = false, result = it) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }

    fun verificarAgora() {
        viewModelScope.launch {
            _state.value = _state.value.copy(verifying = true)
            runCatching { repository.verificarAgora() }
            load()
            _state.value = _state.value.copy(verifying = false)
        }
    }
}
