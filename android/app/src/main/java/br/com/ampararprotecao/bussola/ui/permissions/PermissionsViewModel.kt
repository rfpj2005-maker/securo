package br.com.ampararprotecao.bussola.ui.permissions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceMember
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaWorkspacesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** The shared team workspace — Raimundo also owns a second business
 * workspace ("Pimenta") that's just his own, with no other members, so
 * this screen always targets the real one explicitly rather than
 * whichever workspace happens to be selected in the switcher right now
 * (matches the same fix in Painel Amparar's own bussola-auth.js). */
private const val AMPARAR_WORKSPACE_ID = "170e8fe6-7f6e-4a41-8687-26b6fdc31817"

/** Mirrors backend `member_access_service.FEATURE_IDS` — see that file for
 * why `pa_carne`/`pa_cobranca`/`pa_dashboard` exist alongside the older
 * Bússola-only ids. */
val PERMISSION_CATALOG = listOf(
    "tasks" to "Tarefas",
    "calendar" to "Calendário",
    "meetings" to "Reuniões",
    "cameras" to "Câmeras",
    "siprov" to "Siprov",
    "inadimplencia" to "Painel Amparar (web)",
    "pa_carne" to "Carnê",
    "pa_cobranca" to "Cobrança",
    "pa_dashboard" to "Dashboard Amparar",
    "pa_rastreadores" to "Rastreadores",
    "pa_cancelados" to "Cancelados",
)

data class PermissionsUiState(
    val loading: Boolean = true,
    val members: List<WorkspaceMember> = emptyList(),
    val saving: String? = null, // user_id currently being saved
    val error: String? = null,
)

@HiltViewModel
class PermissionsViewModel @Inject constructor(
    private val repository: BussolaWorkspacesRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(PermissionsUiState())
    val state: StateFlow<PermissionsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            runCatching { repository.members(AMPARAR_WORKSPACE_ID) }
                .onSuccess { _state.value = _state.value.copy(loading = false, members = it) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
    }

    fun toggle(member: WorkspaceMember, featureId: String, enabled: Boolean) {
        val newHidden = if (enabled) {
            member.hiddenModules - featureId
        } else {
            member.hiddenModules + featureId
        }
        viewModelScope.launch {
            _state.value = _state.value.copy(saving = member.userId)
            runCatching { repository.setMemberModules(AMPARAR_WORKSPACE_ID, member.userId, newHidden) }
                .onSuccess { load() }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
            _state.value = _state.value.copy(saving = null)
        }
    }
}
