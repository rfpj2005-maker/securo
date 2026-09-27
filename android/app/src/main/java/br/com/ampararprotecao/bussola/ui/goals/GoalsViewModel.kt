package br.com.ampararprotecao.bussola.ui.goals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.Goal
import br.com.ampararprotecao.bussola.data.bussola.model.GoalCreate
import br.com.ampararprotecao.bussola.data.bussola.model.GoalUpdate
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaGoalsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class GoalsUiState(
    val loading: Boolean = true,
    val goals: List<Goal> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class GoalsViewModel @Inject constructor(
    private val repository: BussolaGoalsRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(GoalsUiState())
    val state: StateFlow<GoalsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repository.list() }
                .onSuccess { list -> _state.value = GoalsUiState(loading = false, goals = list.filter { it.status != "archived" }) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }

    fun save(id: String?, name: String, target: String, current: String, targetDate: String?, onDone: () -> Unit) {
        viewModelScope.launch {
            runCatching {
                if (id == null) {
                    repository.create(GoalCreate(name = name, targetAmount = target, currentAmount = current, targetDate = targetDate))
                } else {
                    repository.update(id, GoalUpdate(name = name, targetAmount = target, currentAmount = current, targetDate = targetDate))
                }
            }.onSuccess { load(); onDone() }
        }
    }

    fun delete(id: String, onDone: () -> Unit) {
        viewModelScope.launch {
            runCatching { repository.delete(id) }.onSuccess { load(); onDone() }
        }
    }
}
