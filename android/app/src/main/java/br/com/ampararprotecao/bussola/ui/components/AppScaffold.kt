package br.com.ampararprotecao.bussola.ui.components

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import br.com.ampararprotecao.bussola.ui.SessionViewModel
import br.com.ampararprotecao.bussola.ui.navigation.DRAWER_ITEMS
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
    val painelConnected = sessionViewModel.painelAmpararConnected
    val isSuperuser = sessionViewModel.isSuperuser

    val visibleItems = DRAWER_ITEMS.filter { item ->
        (!item.requiresPainelAmparar || painelConnected) &&
            (!item.requiresSuperuser || isSuperuser) &&
            sessionViewModel.hasFeature(item.featureId)
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Text(
                    currentWorkspace?.name ?: "Bússola",
                    modifier = Modifier.padding(16.dp),
                    style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                )
                visibleItems.forEach { item ->
                    NavigationDrawerItem(
                        label = { Text(item.labelPtBr) },
                        selected = currentRoute == item.screen.route,
                        onClick = {
                            scope.launch { drawerState.close() }
                            onNavigate(item.screen)
                        },
                        modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding),
                    )
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
