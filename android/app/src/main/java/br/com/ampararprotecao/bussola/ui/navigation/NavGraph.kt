package br.com.ampararprotecao.bussola.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import br.com.ampararprotecao.bussola.ui.SessionViewModel
import br.com.ampararprotecao.bussola.ui.accounts.AccountsScreen
import br.com.ampararprotecao.bussola.ui.carne.CarneScreen
import br.com.ampararprotecao.bussola.ui.cobranca.CobrancaScreen
import br.com.ampararprotecao.bussola.ui.components.AppScaffold
import br.com.ampararprotecao.bussola.ui.dashboard.DashboardScreen
import br.com.ampararprotecao.bussola.ui.login.LoginScreen
import br.com.ampararprotecao.bussola.ui.login.TwoFactorScreen
import br.com.ampararprotecao.bussola.ui.paineldashboard.PainelDashboardScreen
import br.com.ampararprotecao.bussola.ui.permissions.PermissionsScreen
import br.com.ampararprotecao.bussola.ui.transactions.TransactionEditScreen
import br.com.ampararprotecao.bussola.ui.transactions.TransactionsListScreen

private data class TfaChallenge(val tempToken: String, val methods: List<String>)

@Composable
fun BussolaNavHost() {
    val navController = rememberNavController()
    val sessionViewModel: SessionViewModel = hiltViewModel()
    val loggedIn by sessionViewModel.loggedIn.collectAsState()
    var tfaChallenge by remember { mutableStateOf<TfaChallenge?>(null) }

    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route ?: Screen.Dashboard.route

    // A 401 anywhere clears the token store; when that happens outside of
    // an explicit logout tap, bounce straight back to the login screen.
    LaunchedEffect(loggedIn) {
        if (!loggedIn && currentRoute != Screen.Login.route && currentRoute != Screen.TwoFactor.route) {
            navController.navigate(Screen.Login.route) {
                popUpTo(0)
            }
        }
    }

    fun goMain(screen: Screen) {
        navController.navigate(screen.route) {
            popUpTo(Screen.Login.route) { inclusive = true }
            launchSingleTop = true
        }
    }

    NavHost(navController = navController, startDestination = if (loggedIn) Screen.Dashboard.route else Screen.Login.route) {
        composable(Screen.Login.route) {
            // SSO (2026-09-16): logging into Bússola is the whole flow now —
            // Painel Amparar trusts the same token, no separate connect step.
            // SessionViewModel.refreshWorkspaces() (called by these screens
            // on success) also probes Painel Amparar once in the background
            // to know whether to show its menu items at all.
            LoginScreen(
                sessionViewModel = sessionViewModel,
                onNeedsTwoFactor = { tempToken, methods ->
                    tfaChallenge = TfaChallenge(tempToken, methods)
                    navController.navigate(Screen.TwoFactor.route)
                },
                onLoggedIn = { goMain(Screen.Dashboard) },
            )
        }
        composable(Screen.TwoFactor.route) {
            val challenge = tfaChallenge
            if (challenge != null) {
                TwoFactorScreen(
                    sessionViewModel = sessionViewModel,
                    tempToken = challenge.tempToken,
                    methods = challenge.methods,
                    onLoggedIn = { goMain(Screen.Dashboard) },
                )
            }
        }

        composable(Screen.Dashboard.route) {
            AppScaffold(sessionViewModel, "Dashboard", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                DashboardScreen(modifier = padding)
            }
        }
        composable(Screen.Transactions.route) {
            AppScaffold(sessionViewModel, "Transações", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                TransactionsListScreen(modifier = padding, onOpenTransaction = { id -> navController.navigate(Screen.TransactionEdit.route(id)) })
            }
        }
        composable(
            Screen.TransactionEdit.route,
            arguments = listOf(
                navArgument("id") {
                    type = androidx.navigation.NavType.StringType
                    defaultValue = ""
                    nullable = false
                },
            ),
        ) { entry ->
            val id = entry.arguments?.getString("id")?.ifBlank { null }
            AppScaffold(sessionViewModel, if (id == null) "Nova transação" else "Editar transação", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                TransactionEditScreen(
                    modifier = padding,
                    transactionId = id,
                    onSaved = { navController.popBackStack() },
                    onDelete = { navController.popBackStack() },
                )
            }
        }
        composable(Screen.Accounts.route) {
            AppScaffold(sessionViewModel, "Contas", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                AccountsScreen(modifier = padding)
            }
        }
        composable(Screen.Carne.route) {
            AppScaffold(sessionViewModel, "Carnê", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                CarneScreen(modifier = padding)
            }
        }
        composable(Screen.Cobranca.route) {
            AppScaffold(sessionViewModel, "Cobrança", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                CobrancaScreen(modifier = padding)
            }
        }
        composable(Screen.PainelDashboard.route) {
            AppScaffold(sessionViewModel, "Dashboard Amparar", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                PainelDashboardScreen(modifier = padding)
            }
        }
        composable(Screen.Permissions.route) {
            AppScaffold(sessionViewModel, "Permissões", currentRoute, onNavigate = { navController.navigate(it.route) }, onLogout = { sessionViewModel.logout() }) { padding ->
                PermissionsScreen(modifier = padding)
            }
        }
    }
}
