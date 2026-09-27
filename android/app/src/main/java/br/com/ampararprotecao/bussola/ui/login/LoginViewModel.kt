package br.com.ampararprotecao.bussola.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaAuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface LoginUiState {
    data object Idle : LoginUiState
    data object Loading : LoginUiState
    data class NeedsTwoFactor(val tempToken: String, val methods: List<String>) : LoginUiState
    data object Success : LoginUiState
    data class Error(val message: String) : LoginUiState
}

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: BussolaAuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<LoginUiState>(LoginUiState.Idle)
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun login(username: String, password: String) {
        if (username.isBlank() || password.isBlank()) return
        _state.value = LoginUiState.Loading
        viewModelScope.launch {
            runCatching { authRepository.login(username, password) }
                .onSuccess { response ->
                    if (response.requiresTfa && response.tempToken != null) {
                        _state.value = LoginUiState.NeedsTwoFactor(response.tempToken, response.availableMethods)
                    } else {
                        runCatching { authRepository.completeLogin(response) }
                            .onSuccess { _state.value = LoginUiState.Success }
                            .onFailure { _state.value = LoginUiState.Error(it.message ?: "Falha ao concluir login") }
                    }
                }
                .onFailure { _state.value = LoginUiState.Error("Usuário ou senha inválidos") }
        }
    }

    fun verifyTwoFactor(tempToken: String, code: String) {
        if (code.isBlank()) return
        _state.value = LoginUiState.Loading
        viewModelScope.launch {
            runCatching { authRepository.verifyTwoFactor(tempToken, code) }
                .onSuccess { response ->
                    runCatching { authRepository.completeLogin(response) }
                        .onSuccess { _state.value = LoginUiState.Success }
                        .onFailure { _state.value = LoginUiState.Error(it.message ?: "Falha ao concluir login") }
                }
                .onFailure { _state.value = LoginUiState.Error("Código inválido") }
        }
    }

    fun resetError() {
        if (_state.value is LoginUiState.Error) _state.value = LoginUiState.Idle
    }

    fun forgotPassword(email: String, onDone: () -> Unit) {
        viewModelScope.launch {
            runCatching { authRepository.forgotPassword(email) }
            // Same behavior as web either way — never reveal whether the
            // email is registered, so a failure here still shows "check
            // your email" rather than an error.
            onDone()
        }
    }
}
