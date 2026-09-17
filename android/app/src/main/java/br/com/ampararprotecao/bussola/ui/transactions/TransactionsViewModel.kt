package br.com.ampararprotecao.bussola.ui.transactions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.Transaction
import br.com.ampararprotecao.bussola.data.bussola.model.TransactionEditPayload
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaAccountsRepository
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaCategoriesRepository
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaTransactionsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class TransactionsUiState(
    val loading: Boolean = true,
    val items: List<Transaction> = emptyList(),
    val page: Int = 1,
    val hasMore: Boolean = true,
    val query: String = "",
    val categories: List<Category> = emptyList(),
    val accounts: List<Account> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class TransactionsViewModel @Inject constructor(
    private val transactionsRepository: BussolaTransactionsRepository,
    private val categoriesRepository: BussolaCategoriesRepository,
    private val accountsRepository: BussolaAccountsRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(TransactionsUiState())
    val state: StateFlow<TransactionsUiState> = _state.asStateFlow()

    init {
        loadLookups()
        refresh()
    }

    private fun loadLookups() {
        viewModelScope.launch {
            runCatching { categoriesRepository.list() }.onSuccess { _state.value = _state.value.copy(categories = it) }
            runCatching { accountsRepository.list() }.onSuccess { _state.value = _state.value.copy(accounts = it) }
        }
    }

    fun refresh(query: String = _state.value.query) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null, query = query)
            runCatching { transactionsRepository.list(page = 1, query = query.ifBlank { null }) }
                .onSuccess { page ->
                    _state.value = _state.value.copy(
                        loading = false,
                        items = page.items,
                        page = 1,
                        hasMore = page.items.size >= 30,
                    )
                }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }

    fun loadMore() {
        if (!_state.value.hasMore || _state.value.loading) return
        val nextPage = _state.value.page + 1
        viewModelScope.launch {
            runCatching { transactionsRepository.list(page = nextPage, query = _state.value.query.ifBlank { null }) }
                .onSuccess { page ->
                    _state.value = _state.value.copy(
                        items = _state.value.items + page.items,
                        page = nextPage,
                        hasMore = page.items.size >= 30,
                    )
                }
        }
    }

    fun deleteTransaction(id: String) {
        viewModelScope.launch {
            runCatching { transactionsRepository.delete(id) }.onSuccess { refresh() }
        }
    }
}

sealed interface TransactionEditUiState {
    data object Loading : TransactionEditUiState
    data class Ready(
        val transaction: Transaction?,
        val categories: List<Category>,
        val accounts: List<Account>,
        val saving: Boolean = false,
        val error: String? = null,
    ) : TransactionEditUiState
    data object Saved : TransactionEditUiState
}

@HiltViewModel
class TransactionEditViewModel @Inject constructor(
    private val transactionsRepository: BussolaTransactionsRepository,
    private val categoriesRepository: BussolaCategoriesRepository,
    private val accountsRepository: BussolaAccountsRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<TransactionEditUiState>(TransactionEditUiState.Loading)
    val state: StateFlow<TransactionEditUiState> = _state.asStateFlow()

    fun load(id: String?) {
        viewModelScope.launch {
            _state.value = TransactionEditUiState.Loading
            val categories = runCatching { categoriesRepository.list() }.getOrDefault(emptyList())
            val accounts = runCatching { accountsRepository.list() }.getOrDefault(emptyList())
            val existing = if (id != null) {
                runCatching { transactionsRepository.get(id) }.getOrNull()
            } else null
            _state.value = TransactionEditUiState.Ready(existing, categories, accounts)
        }
    }

    fun save(id: String?, payload: TransactionEditPayload) {
        val current = _state.value as? TransactionEditUiState.Ready ?: return
        _state.value = current.copy(saving = true, error = null)
        viewModelScope.launch {
            val result = if (id != null) {
                runCatching { transactionsRepository.update(id, payload) }
            } else {
                runCatching { transactionsRepository.create(payload) }
            }
            result
                .onSuccess { _state.value = TransactionEditUiState.Saved }
                .onFailure { _state.value = current.copy(saving = false, error = it.message ?: "Falha ao salvar") }
        }
    }
}
