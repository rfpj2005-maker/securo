package br.com.ampararprotecao.bussola.ui.recurring

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransaction
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransactionCreate
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransactionUpdate
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaAccountsRepository
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaCategoriesRepository
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaRecurringRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class RecurringListUiState(
    val loading: Boolean = true,
    val items: List<RecurringTransaction> = emptyList(),
    val accountsById: Map<String, Account> = emptyMap(),
    val categoriesById: Map<String, Category> = emptyMap(),
)

@HiltViewModel
class RecurringViewModel @Inject constructor(
    private val repository: BussolaRecurringRepository,
    private val accountsRepository: BussolaAccountsRepository,
    private val categoriesRepository: BussolaCategoriesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(RecurringListUiState())
    val state: StateFlow<RecurringListUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val items = runCatching { repository.list() }.getOrDefault(emptyList())
            val accounts = runCatching { accountsRepository.list() }.getOrDefault(emptyList())
            val categories = runCatching { categoriesRepository.list() }.getOrDefault(emptyList())
            _state.value = RecurringListUiState(
                loading = false,
                items = items.sortedBy { it.nextOccurrence },
                accountsById = accounts.associateBy { it.id },
                categoriesById = categories.associateBy { it.id },
            )
        }
    }

    fun toggleActive(item: RecurringTransaction) {
        viewModelScope.launch {
            runCatching { repository.update(item.id, RecurringTransactionUpdate(isActive = !item.isActive)) }
                .onSuccess { load() }
        }
    }
}

sealed interface RecurringEditUiState {
    data object Loading : RecurringEditUiState
    data class Ready(
        val item: RecurringTransaction?,
        val accounts: List<Account>,
        val categories: List<Category>,
        val saving: Boolean = false,
        val error: String? = null,
    ) : RecurringEditUiState
    data object Saved : RecurringEditUiState
    data object Deleted : RecurringEditUiState
}

@HiltViewModel
class RecurringEditViewModel @Inject constructor(
    private val repository: BussolaRecurringRepository,
    private val accountsRepository: BussolaAccountsRepository,
    private val categoriesRepository: BussolaCategoriesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<RecurringEditUiState>(RecurringEditUiState.Loading)
    val state: StateFlow<RecurringEditUiState> = _state.asStateFlow()

    fun load(id: String?) {
        viewModelScope.launch {
            _state.value = RecurringEditUiState.Loading
            val accounts = runCatching { accountsRepository.list() }.getOrDefault(emptyList())
            val categories = runCatching { categoriesRepository.list() }.getOrDefault(emptyList())
            val existing = if (id != null) {
                runCatching { repository.list() }.getOrDefault(emptyList()).firstOrNull { it.id == id }
            } else null
            _state.value = RecurringEditUiState.Ready(existing, accounts, categories)
        }
    }

    fun save(id: String?, create: RecurringTransactionCreate, update: RecurringTransactionUpdate) {
        val current = _state.value as? RecurringEditUiState.Ready ?: return
        _state.value = current.copy(saving = true, error = null)
        viewModelScope.launch {
            val result = if (id != null) runCatching { repository.update(id, update) } else runCatching { repository.create(create) }
            result
                .onSuccess { _state.value = RecurringEditUiState.Saved }
                .onFailure { _state.value = current.copy(saving = false, error = it.message ?: "Falha ao salvar") }
        }
    }

    fun delete(id: String) {
        viewModelScope.launch {
            runCatching { repository.delete(id) }.onSuccess { _state.value = RecurringEditUiState.Deleted }
        }
    }
}
