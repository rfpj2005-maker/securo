package br.com.ampararprotecao.bussola.ui.tasks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.Task
import br.com.ampararprotecao.bussola.data.bussola.model.TaskCreate
import br.com.ampararprotecao.bussola.data.bussola.model.TaskUpdate
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaTasksRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class TasksUiState(
    val loading: Boolean = true,
    val tasks: List<Task> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class TasksViewModel @Inject constructor(
    private val repository: BussolaTasksRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(TasksUiState())
    val state: StateFlow<TasksUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repository.list() }
                .onSuccess { _state.value = TasksUiState(loading = false, tasks = it) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }

    fun toggleStatus(task: Task) {
        val newStatus = if (task.status == "completed") "pending" else "completed"
        viewModelScope.launch {
            runCatching { repository.update(task.id, TaskUpdate(status = newStatus)) }
                .onSuccess { load() }
        }
    }
}

sealed interface TaskEditUiState {
    data object Loading : TaskEditUiState
    data class Ready(
        val task: Task?,
        val saving: Boolean = false,
        val error: String? = null,
    ) : TaskEditUiState
    data object Saved : TaskEditUiState
    data object Deleted : TaskEditUiState
}

@HiltViewModel
class TaskEditViewModel @Inject constructor(
    private val repository: BussolaTasksRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<TaskEditUiState>(TaskEditUiState.Loading)
    val state: StateFlow<TaskEditUiState> = _state.asStateFlow()

    private var currentId: String? = null

    fun load(id: String?) {
        currentId = id
        viewModelScope.launch {
            _state.value = TaskEditUiState.Loading
            val existing = if (id != null) runCatching { repository.get(id) }.getOrNull() else null
            _state.value = TaskEditUiState.Ready(existing)
        }
    }

    private fun refreshReady() {
        val id = currentId ?: return
        viewModelScope.launch {
            runCatching { repository.get(id) }.onSuccess { fresh ->
                val current = _state.value as? TaskEditUiState.Ready ?: return@onSuccess
                _state.value = current.copy(task = fresh)
            }
        }
    }

    fun save(id: String?, create: TaskCreate, update: TaskUpdate) {
        val current = _state.value as? TaskEditUiState.Ready ?: return
        _state.value = current.copy(saving = true, error = null)
        viewModelScope.launch {
            val result = if (id != null) runCatching { repository.update(id, update) }
            else runCatching { repository.create(create) }
            result
                .onSuccess { _state.value = TaskEditUiState.Saved }
                .onFailure { _state.value = current.copy(saving = false, error = it.message ?: "Falha ao salvar") }
        }
    }

    fun delete(id: String) {
        viewModelScope.launch {
            runCatching { repository.delete(id) }.onSuccess { _state.value = TaskEditUiState.Deleted }
        }
    }

    fun addSubtask(title: String) {
        val id = currentId ?: return
        if (title.isBlank()) return
        viewModelScope.launch {
            runCatching { repository.createSubtask(id, title) }.onSuccess { refreshReady() }
        }
    }

    fun toggleSubtask(subtaskId: String, isDone: Boolean) {
        val id = currentId ?: return
        viewModelScope.launch {
            runCatching { repository.toggleSubtask(id, subtaskId, isDone) }.onSuccess { refreshReady() }
        }
    }

    fun renameSubtask(subtaskId: String, title: String) {
        val id = currentId ?: return
        if (title.isBlank()) return
        viewModelScope.launch {
            runCatching { repository.renameSubtask(id, subtaskId, title) }.onSuccess { refreshReady() }
        }
    }

    fun deleteSubtask(subtaskId: String) {
        val id = currentId ?: return
        viewModelScope.launch {
            runCatching { repository.deleteSubtask(id, subtaskId) }.onSuccess { refreshReady() }
        }
    }
}
