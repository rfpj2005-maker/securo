package br.com.ampararprotecao.bussola.ui.categories

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.CategoryCreate
import br.com.ampararprotecao.bussola.data.bussola.model.CategoryGroup
import br.com.ampararprotecao.bussola.data.bussola.model.CategoryUpdate
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaCategoriesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

val CATEGORY_COLOR_SWATCHES = listOf(
    "#EF4444", "#F97316", "#F59E0B", "#EAB308", "#84CC16",
    "#10B981", "#14B8A6", "#06B6D4", "#3B82F6", "#6366F1",
    "#8B5CF6", "#D946EF", "#EC4899", "#6B7280",
)

data class CategoriesUiState(
    val loading: Boolean = true,
    val groups: List<CategoryGroup> = emptyList(),
    val ungrouped: List<Category> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class CategoriesViewModel @Inject constructor(
    private val repository: BussolaCategoriesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CategoriesUiState())
    val state: StateFlow<CategoriesUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching {
                val categories = repository.list()
                val groups = repository.groups()
                val byGroup = categories.groupBy { it.groupId }
                val filledGroups = groups.map { g -> g.copy(categories = byGroup[g.id] ?: emptyList()) }
                val ungrouped = byGroup[null] ?: emptyList()
                filledGroups to ungrouped
            }.onSuccess { (groups, ungrouped) ->
                _state.value = CategoriesUiState(loading = false, groups = groups, ungrouped = ungrouped)
            }.onFailure {
                _state.value = _state.value.copy(loading = false, error = it.message)
            }
        }
    }

    fun save(id: String?, name: String, color: String, groupId: String?, onDone: () -> Unit) {
        viewModelScope.launch {
            runCatching {
                if (id == null) {
                    repository.create(CategoryCreate(name = name, color = color, groupId = groupId))
                } else {
                    repository.update(id, CategoryUpdate(name = name, color = color, groupId = groupId))
                }
            }.onSuccess {
                load()
                onDone()
            }
        }
    }

    fun delete(id: String, onDone: () -> Unit) {
        viewModelScope.launch {
            runCatching { repository.delete(id) }.onSuccess {
                load()
                onDone()
            }
        }
    }
}
