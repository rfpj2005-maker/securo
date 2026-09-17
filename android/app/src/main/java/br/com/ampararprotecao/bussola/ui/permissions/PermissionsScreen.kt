package br.com.ampararprotecao.bussola.ui.permissions

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceMember

/** Same catalog and same `PUT /workspaces/{id}/members/{userId}/modules`
 * endpoint as the web's workspace-settings "manage modules" dialog — this
 * screen is just a mobile-friendly version of that, not a separate
 * permission system. Owners can't be restricted (mirrors the backend
 * check), so they're shown without toggles. */
@Composable
fun PermissionsScreen(modifier: Modifier = Modifier, viewModel: PermissionsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    if (state.loading) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    LazyColumn(modifier = modifier.fillMaxSize().padding(16.dp)) {
        state.error?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }

        items(state.members) { member ->
            MemberPermissionsCard(
                member = member,
                saving = state.saving == member.userId,
                onToggle = { featureId, enabled -> viewModel.toggle(member, featureId, enabled) },
            )
        }
    }
}

@Composable
private fun MemberPermissionsCard(
    member: WorkspaceMember,
    saving: Boolean,
    onToggle: (String, Boolean) -> Unit,
) {
    Card(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        Column(Modifier.padding(16.dp)) {
            Text(member.displayName, style = MaterialTheme.typography.titleMedium)
            Text(member.role, style = MaterialTheme.typography.bodySmall)

            if (member.role == "owner") {
                Text(
                    "Dono do workspace — sempre vê tudo",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 8.dp),
                )
                return@Card
            }

            PERMISSION_CATALOG.forEach { (id, label) ->
                Row(
                    Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceBetween,
                ) {
                    Text(label)
                    Switch(
                        checked = !member.hiddenModules.contains(id),
                        onCheckedChange = { onToggle(id, it) },
                        enabled = !saving,
                    )
                }
            }
        }
    }
}
