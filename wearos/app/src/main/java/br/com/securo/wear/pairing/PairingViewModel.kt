package br.com.securo.wear.pairing

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.securo.wear.data.ServerSettings
import br.com.securo.wear.data.TokenStore
import br.com.securo.wear.network.ApiClient
import br.com.securo.wear.network.RedeemRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed interface PairingUiState {
    data object Idle : PairingUiState
    data object Loading : PairingUiState
    data object Error : PairingUiState
    data object Success : PairingUiState
}

class PairingViewModel(
    private val serverSettings: ServerSettings,
    private val tokenStore: TokenStore,
) : ViewModel() {
    private val _state = MutableStateFlow<PairingUiState>(PairingUiState.Idle)
    val state: StateFlow<PairingUiState> = _state

    /** [rawCode] is whatever the user typed/spoke via RemoteInput —
     *  trimmed and digit-filtered here so a stray space or a voice
     *  transcription like "1 2 3 4 5 6" still redeems correctly. */
    fun redeem(rawCode: String) {
        val code = rawCode.filter { it.isDigit() }
        if (code.length != 6) {
            _state.value = PairingUiState.Error
            return
        }
        _state.value = PairingUiState.Loading
        viewModelScope.launch {
            try {
                val api = ApiClient.create(serverSettings, tokenStore)
                val response = api.redeemWatchPairing(RedeemRequest(code))
                val token = response.body()?.access_token
                if (response.isSuccessful && !token.isNullOrBlank()) {
                    tokenStore.accessToken = token
                    _state.value = PairingUiState.Success
                } else {
                    _state.value = PairingUiState.Error
                }
            } catch (e: Exception) {
                _state.value = PairingUiState.Error
            }
        }
    }

    fun resetError() {
        _state.value = PairingUiState.Idle
    }
}
