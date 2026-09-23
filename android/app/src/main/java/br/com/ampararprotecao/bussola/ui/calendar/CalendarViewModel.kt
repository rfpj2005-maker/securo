package br.com.ampararprotecao.bussola.ui.calendar

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventCreate
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventRead
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventUpdate
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaCalendarRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.LocalDate
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CalendarUiState(
    val loading: Boolean = true,
    val connected: Boolean = true,
    val events: List<CalendarEventRead> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class CalendarViewModel @Inject constructor(
    private val repository: BussolaCalendarRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CalendarUiState())
    val state: StateFlow<CalendarUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            val status = runCatching { repository.status() }.getOrNull()
            if (status?.connected != true) {
                _state.value = CalendarUiState(loading = false, connected = false)
                return@launch
            }
            // Agenda window: yesterday through +60 days — enough to show
            // what's coming up without a full month-grid UI.
            val start = LocalDate.now().minusDays(1).toString() + "T00:00:00Z"
            val end = LocalDate.now().plusDays(60).toString() + "T00:00:00Z"
            runCatching { repository.events(start, end) }
                .onSuccess { _state.value = CalendarUiState(loading = false, connected = true, events = it) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }
}

sealed interface CalendarEventEditUiState {
    data object Loading : CalendarEventEditUiState
    data class Ready(
        val event: CalendarEventRead?,
        val saving: Boolean = false,
        val error: String? = null,
    ) : CalendarEventEditUiState
    data object Saved : CalendarEventEditUiState
    data object Deleted : CalendarEventEditUiState
}

@HiltViewModel
class CalendarEventEditViewModel @Inject constructor(
    private val repository: BussolaCalendarRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<CalendarEventEditUiState>(CalendarEventEditUiState.Loading)
    val state: StateFlow<CalendarEventEditUiState> = _state.asStateFlow()

    fun load(id: String?, calendarId: String?) {
        viewModelScope.launch {
            _state.value = CalendarEventEditUiState.Loading
            val existing = if (id != null) {
                // No single-event GET endpoint — find it in a wide window.
                val start = LocalDate.now().minusYears(1).toString() + "T00:00:00Z"
                val end = LocalDate.now().plusYears(1).toString() + "T00:00:00Z"
                runCatching { repository.events(start, end) }.getOrNull()?.firstOrNull { it.id == id && (calendarId == null || it.calendarId == calendarId) }
            } else null
            _state.value = CalendarEventEditUiState.Ready(existing)
        }
    }

    fun save(id: String?, calendarId: String?, create: CalendarEventCreate, update: CalendarEventUpdate) {
        val current = _state.value as? CalendarEventEditUiState.Ready ?: return
        _state.value = current.copy(saving = true, error = null)
        viewModelScope.launch {
            val result = if (id != null && calendarId != null) {
                runCatching { repository.updateEvent(id, calendarId, update) }
            } else {
                runCatching { repository.createEvent(create) }
            }
            result
                .onSuccess { _state.value = CalendarEventEditUiState.Saved }
                .onFailure { _state.value = current.copy(saving = false, error = it.message ?: "Falha ao salvar") }
        }
    }

    fun delete(id: String, calendarId: String) {
        viewModelScope.launch {
            runCatching { repository.deleteEvent(id, calendarId) }.onSuccess { _state.value = CalendarEventEditUiState.Deleted }
        }
    }
}
