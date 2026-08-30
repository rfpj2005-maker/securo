package br.com.securo.wear.calendar

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.securo.wear.data.ServerSettings
import br.com.securo.wear.data.TokenStore
import br.com.securo.wear.network.ApiClient
import br.com.securo.wear.network.CalendarEventDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.temporal.ChronoUnit

sealed interface CalendarUiState {
    data object Loading : CalendarUiState
    data object NotConnected : CalendarUiState
    data object Error : CalendarUiState
    data class Loaded(val events: List<CalendarEventDto>) : CalendarUiState
}

// How far ahead the agenda looks — a watch screen has room for a
// handful of rows, not a full month; matches the "next few days" scope
// from planning.
private val AGENDA_WINDOW_DAYS = 3L

class CalendarViewModel(
    serverSettings: ServerSettings,
    tokenStore: TokenStore,
) : ViewModel() {
    private val api = ApiClient.create(serverSettings, tokenStore)
    private val _state = MutableStateFlow<CalendarUiState>(CalendarUiState.Loading)
    val state: StateFlow<CalendarUiState> = _state

    init {
        refresh()
    }

    fun refresh() {
        _state.value = CalendarUiState.Loading
        viewModelScope.launch {
            try {
                val status = api.calendarStatus().body()
                if (status?.connected != true) {
                    _state.value = CalendarUiState.NotConnected
                    return@launch
                }
                val now = Instant.now()
                val response = api.listCalendarEvents(
                    start = now.toString(),
                    end = now.plus(AGENDA_WINDOW_DAYS, ChronoUnit.DAYS).toString(),
                )
                val body = response.body()
                _state.value = if (response.isSuccessful && body != null) {
                    CalendarUiState.Loaded(body)
                } else {
                    CalendarUiState.Error
                }
            } catch (e: Exception) {
                _state.value = CalendarUiState.Error
            }
        }
    }
}
