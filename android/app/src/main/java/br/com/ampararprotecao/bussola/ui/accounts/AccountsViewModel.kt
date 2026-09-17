package br.com.ampararprotecao.bussola.ui.accounts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaAccountsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AccountsUiState(
    val loading: Boolean = true,
    val accounts: List<Account> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class AccountsViewModel @Inject constructor(
    private val repository: BussolaAccountsRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(AccountsUiState())
    val state: StateFlow<AccountsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repository.list() }
                .onSuccess { _state.value = AccountsUiState(loading = false, accounts = it) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }
}
