package br.com.securo.wear.tasks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.securo.wear.data.ServerSettings
import br.com.securo.wear.data.TokenStore
import br.com.securo.wear.network.ApiClient
import br.com.securo.wear.network.TaskDto
import br.com.securo.wear.network.TaskStatusUpdate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed interface TasksUiState {
    data object Loading : TasksUiState
    data object Error : TasksUiState
    data class Loaded(val tasks: List<TaskDto>) : TasksUiState
}

class TasksViewModel(
    serverSettings: ServerSettings,
    tokenStore: TokenStore,
) : ViewModel() {
    private val api = ApiClient.create(serverSettings, tokenStore)
    private val _state = MutableStateFlow<TasksUiState>(TasksUiState.Loading)
    val state: StateFlow<TasksUiState> = _state

    init {
        refresh()
    }

    fun refresh() {
        _state.value = TasksUiState.Loading
        viewModelScope.launch {
            try {
                val response = api.listTasks(status = "pending")
                val body = response.body()
                _state.value = if (response.isSuccessful && body != null) {
                    TasksUiState.Loaded(body)
                } else {
                    TasksUiState.Error
                }
            } catch (e: Exception) {
                _state.value = TasksUiState.Error
            }
        }
    }

    /** Optimistic: drops the task from the visible list immediately, then
     *  reconciles with a refresh either way — a failed PATCH just brings
     *  it back on the next load rather than needing its own undo path. */
    fun complete(task: TaskDto) {
        val current = _state.value
        if (current is TasksUiState.Loaded) {
            _state.value = TasksUiState.Loaded(current.tasks.filterNot { it.id == task.id })
        }
        viewModelScope.launch {
            try {
                api.updateTaskStatus(task.id, TaskStatusUpdate(status = "completed"))
            } catch (e: Exception) {
                // Swallowed on purpose: refresh() reconciles state either
                // way, and there's no error-toast surface on this screen
                // worth building for a single failed tap.
            } finally {
                refresh()
            }
        }
    }
}
