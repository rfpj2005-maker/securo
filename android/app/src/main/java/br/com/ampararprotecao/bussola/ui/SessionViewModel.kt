package br.com.ampararprotecao.bussola.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.BussolaTokenStore
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceRead
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaWorkspacesRepository
import br.com.ampararprotecao.bussola.data.painelamparar.repository.PainelAuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Activity-scoped session state shared by the drawer and every screen that
 * needs to know "which workspace, which features, am I the superuser, is
 * Painel Amparar linked" — one Hilt instance for the whole nav graph
 * (obtained via `hiltViewModel(activityScope)` at the root), not one per
 * screen.
 */
@HiltViewModel
class SessionViewModel @Inject constructor(
    private val workspacesRepository: BussolaWorkspacesRepository,
    private val painelAuthRepository: PainelAuthRepository,
    val bussolaTokenStore: BussolaTokenStore,
) : ViewModel() {

    private val _workspaces = MutableStateFlow<List<WorkspaceRead>>(emptyList())
    val workspaces: StateFlow<List<WorkspaceRead>> = _workspaces.asStateFlow()

    private val _currentWorkspace = MutableStateFlow<WorkspaceRead?>(null)
    val currentWorkspace: StateFlow<WorkspaceRead?> = _currentWorkspace.asStateFlow()

    // null = not checked yet (treat as not-linked for menu purposes until
    // it resolves, same as before login). SSO (2026-09-16): there's no
    // separate Painel Amparar session to be "connected" or not anymore —
    // this just reflects whether this Bússola account has been linked to
    // a Painel Amparar identity (usuarios.js `vincular`), which only the
    // owner can do server-side, not something to "connect" from the app.
    private val _painelAmpararLinked = MutableStateFlow<Boolean?>(null)
    // Exposed as a StateFlow (not a plain get()-only Boolean) so the drawer
    // actually recomposes once the async /api/config probe resolves —
    // a plain property read here isn't observed by Compose, so the drawer
    // would keep hiding Carnê/Cobrança/Dashboard Amparar until some
    // unrelated recomposition happened to run after the check finished.
    val painelAmpararLinked: StateFlow<Boolean?> = _painelAmpararLinked.asStateFlow()

    val loggedIn: StateFlow<Boolean> = bussolaTokenStore.loggedIn
    val isSuperuser: Boolean get() = bussolaTokenStore.isSuperuser

    fun refreshWorkspaces() {
        viewModelScope.launch {
            runCatching { workspacesRepository.list() }.onSuccess { list ->
                _workspaces.value = list
                val activeId = bussolaTokenStore.workspaceId
                _currentWorkspace.value = list.firstOrNull { it.id == activeId } ?: list.firstOrNull()
            }
        }
        viewModelScope.launch {
            _painelAmpararLinked.value = runCatching { painelAuthRepository.config() }.isSuccess
        }
    }

    fun switchWorkspace(workspace: WorkspaceRead) {
        workspacesRepository.switchTo(workspace)
        _currentWorkspace.value = workspace
    }

    fun hasFeature(featureId: String?): Boolean {
        if (featureId == null) return true
        return currentWorkspace.value?.hasFeature(featureId) == true
    }

    fun hasModule(moduleId: String?): Boolean {
        if (moduleId == null) return true
        return currentWorkspace.value?.hasModule(moduleId) == true
    }

    fun logout() {
        bussolaTokenStore.clear()
        _workspaces.value = emptyList()
        _currentWorkspace.value = null
        _painelAmpararLinked.value = null
    }
}
