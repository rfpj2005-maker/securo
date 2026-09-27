package br.com.ampararprotecao.bussola.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import br.com.ampararprotecao.bussola.ui.SessionViewModel
import br.com.ampararprotecao.bussola.ui.navigation.DRAWER_ITEMS
import br.com.ampararprotecao.bussola.ui.navigation.DrawerItem
import br.com.ampararprotecao.bussola.ui.navigation.Screen
import kotlinx.coroutines.launch

/** Shared shell for every screen past login: unified drawer menu (filtered
 * by workspace `enabled_features`, Painel Amparar connection, and
 * superuser status), top bar with the current screen title. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScaffold(
    sessionViewModel: SessionViewModel,
    title: String,
    currentRoute: String,
    onNavigate: (Screen) -> Unit,
    onLogout: () -> Unit,
    content: @Composable (Modifier) -> Unit,
) {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val currentWorkspace by sessionViewModel.currentWorkspace.collectAsState()
    val workspaces by sessionViewModel.workspaces.collectAsState()
    val painelLinked by sessionViewModel.painelAmpararLinked.collectAsState()
    val painelConnected = painelLinked == true
    val isSuperuser = sessionViewModel.isSuperuser
    var workspaceMenuExpanded by remember { mutableStateOf(false) }

    val visibleItems = DRAWER_ITEMS.filter { item ->
        (!item.requiresPainelAmparar || painelConnected) &&
            (!item.requiresSuperuser || isSuperuser) &&
            sessionViewModel.hasFeature(item.featureId) &&
            sessionViewModel.hasModule(item.moduleId)
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                if (workspaces.size > 1) {
                    androidx.compose.foundation.layout.Box {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { workspaceMenuExpanded = true }
                            .padding(16.dp),
                    ) {
                        Text(
                            currentWorkspace?.name ?: "Bússola",
                            style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                        )
                        Icon(Icons.Filled.ExpandMore, contentDescription = "Trocar workspace")
                    }
                    DropdownMenu(expanded = workspaceMenuExpanded, onDismissRequest = { workspaceMenuExpanded = false }) {
                        workspaces.forEach { ws ->
                            DropdownMenuItem(
                                text = { Text(ws.name) },
                                onClick = {
                                    workspaceMenuExpanded = false
                                    scope.launch { drawerState.close() }
                                    sessionViewModel.switchWorkspace(ws)
                                    // Land back on a fresh Dashboard so the
                                    // new workspace's data actually loads —
                                    // existing screens don't observe
                                    // currentWorkspace themselves.
                                    onNavigate(Screen.Dashboard)
                                },
                            )
                        }
                    }
                    }
                } else {
                    Text(
                        currentWorkspace?.name ?: "Bússola",
                        modifier = Modifier.padding(16.dp),
                        style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                    )
                }
                val expandedGroups = remember { mutableStateMapOf<String, Boolean>() }
                val renderedGroups = remember { mutableSetOf<String>() }
                renderedGroups.clear()
                visibleItems.forEach { item ->
                    val group = item.groupLabel
                    if (group == null) {
                        NavigationDrawerItem(
                            label = { Text(item.labelPtBr) },
                            selected = currentRoute == item.screen.route,
                            onClick = {
                                scope.launch { drawerState.close() }
                                onNavigate(item.screen)
                            },
                            modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding),
                        )
                    } else if (renderedGroups.add(group)) {
                        val children = visibleItems.filter { it.groupLabel == group }
                        val autoExpand = children.any { it.screen.route == currentRoute }
                        val expanded = expandedGroups[group] ?: autoExpand
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { expandedGroups[group] = !expanded }
                                .padding(horizontal = 28.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(group, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                            Icon(
                                if (expanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                                contentDescription = if (expanded) "Recolher" else "Expandir",
                            )
                        }
                        if (expanded) {
                            children.forEach { child ->
                                NavigationDrawerItem(
                                    label = { Text(child.labelPtBr) },
                                    selected = currentRoute == child.screen.route,
                                    onClick = {
                                        scope.launch { drawerState.close() }
                                        onNavigate(child.screen)
                                    },
                                    modifier = Modifier.padding(start = 16.dp, end = 12.dp),
                                )
                            }
                        }
                    }
                }
                NavigationDrawerItem(
                    label = { Text("Sair") },
                    selected = false,
                    onClick = { scope.launch { drawerState.close() }; onLogout() },
                    modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding),
                )
            }
        },
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(title) },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Filled.Menu, contentDescription = "Menu")
                        }
                    },
                )
            },
        ) { padding ->
            content(Modifier.padding(padding))
        }
    }
}
