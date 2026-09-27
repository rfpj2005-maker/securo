package br.com.ampararprotecao.bussola.ui.budgets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.BudgetCreate
import br.com.ampararprotecao.bussola.data.bussola.model.BudgetUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.BudgetVsActual
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaBudgetsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.LocalDate
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class BudgetsUiState(
    val loading: Boolean = true,
    val month: LocalDate = LocalDate.now().withDayOfMonth(1),
    val items: List<BudgetVsActual> = emptyList(),
    val budgetIdByCategory: Map<String, String> = emptyMap(),
    val error: String? = null,
)

@HiltViewModel
class BudgetsViewModel @Inject constructor(
    private val repository: BussolaBudgetsRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(BudgetsUiState())
    val state: StateFlow<BudgetsUiState> = _state.asStateFlow()

    init { load() }

    private fun monthParam(month: LocalDate) = month.toString()

    fun load() {
        val month = _state.value.month
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching {
                val comparison = repository.comparison(monthParam(month))
                val budgets = repository.list(monthParam(month))
                comparison to budgets.associate { it.categoryId to it.id }
            }.onSuccess { (items, ids) ->
                _state.value = _state.value.copy(loading = false, items = items, budgetIdByCategory = ids)
            }.onFailure {
                _state.value = _state.value.copy(loading = false, error = it.message)
            }
        }
    }

    fun changeMonth(delta: Long) {
        _state.value = _state.value.copy(month = _state.value.month.plusMonths(delta))
        load()
    }

    fun setBudget(categoryId: String, amount: String, recurring: Boolean, onDone: () -> Unit) {
        viewModelScope.launch {
            val existingId = _state.value.budgetIdByCategory[categoryId]
            runCatching {
                if (existingId != null) {
                    repository.update(existingId, BudgetUpdate(amount = amount))
                } else {
                    repository.create(BudgetCreate(categoryId = categoryId, amount = amount, month = monthParam(_state.value.month), isRecurring = recurring))
                }
            }.onSuccess {
                load()
                onDone()
            }
        }
    }

    fun clearBudget(categoryId: String, onDone: () -> Unit) {
        val id = _state.value.budgetIdByCategory[categoryId] ?: return
        viewModelScope.launch {
            runCatching { repository.delete(id) }.onSuccess {
                load()
                onDone()
            }
        }
    }
}
