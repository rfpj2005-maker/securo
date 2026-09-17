package br.com.ampararprotecao.bussola.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.DashboardSummary
import br.com.ampararprotecao.bussola.data.bussola.model.SpendingByCategory
import br.com.ampararprotecao.bussola.data.bussola.model.Transaction
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaDashboardRepository
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaTransactionsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DashboardUiState(
    val loading: Boolean = true,
    val summary: DashboardSummary? = null,
    val spendingByCategory: List<SpendingByCategory> = emptyList(),
    val recentTransactions: List<Transaction> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val dashboardRepository: BussolaDashboardRepository,
    private val transactionsRepository: BussolaTransactionsRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching {
                val summary = dashboardRepository.summary()
                val spending = dashboardRepository.spendingByCategory()
                val recent = transactionsRepository.recent(limit = 10)
                Triple(summary, spending, recent)
            }.onSuccess { (summary, spending, recent) ->
                _state.value = DashboardUiState(loading = false, summary = summary, spendingByCategory = spending, recentTransactions = recent)
            }.onFailure {
                _state.value = _state.value.copy(loading = false, error = it.message ?: "Falha ao carregar o dashboard")
            }
        }
    }
}
