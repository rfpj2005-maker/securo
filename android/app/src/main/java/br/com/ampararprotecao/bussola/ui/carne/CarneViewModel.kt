package br.com.ampararprotecao.bussola.ui.carne

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.painelamparar.model.CarneItem
import br.com.ampararprotecao.bussola.data.painelamparar.model.CarneStatus
import br.com.ampararprotecao.bussola.data.painelamparar.repository.PainelCarneRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CarneUiState(
    val loading: Boolean = true,
    val items: List<CarneItem> = emptyList(),
    val status: CarneStatus? = null,
    val verifying: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class CarneViewModel @Inject constructor(private val repository: PainelCarneRepository) : ViewModel() {

    private val _state = MutableStateFlow(CarneUiState())
    val state: StateFlow<CarneUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching {
                val items = repository.list()
                val status = repository.status()
                items to status
            }.onSuccess { (items, status) ->
                _state.value = CarneUiState(loading = false, items = items, status = status)
            }.onFailure {
                _state.value = _state.value.copy(loading = false, error = it.message)
            }
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
