package br.com.ampararprotecao.bussola.ui.navigation

sealed class Screen(val route: String) {
    data object Login : Screen("login")
    data object TwoFactor : Screen("two_factor")

    data object Dashboard : Screen("dashboard")
    data object Transactions : Screen("transactions")
    data object TransactionEdit : Screen("transaction_edit?id={id}") {
        fun route(id: String? = null) = "transaction_edit?id=${id ?: ""}"
    }
    data object Accounts : Screen("accounts")
    data object Tasks : Screen("tasks")
    data object TaskEdit : Screen("task_edit?id={id}") {
        fun route(id: String? = null) = "task_edit?id=${id ?: ""}"
    }
    data object Calendar : Screen("calendar")
    data object CalendarEventEdit : Screen("calendar_event_edit?id={id}&calendarId={calendarId}") {
        fun route(id: String? = null, calendarId: String? = null) =
            "calendar_event_edit?id=${id ?: ""}&calendarId=${calendarId ?: ""}"
    }
    data object Carne : Screen("carne")
    data object Cobranca : Screen("cobranca")
    data object PainelDashboard : Screen("painel_dashboard")
    data object Permissions : Screen("permissions")
}

/** One entry in the unified drawer menu. `featureId` (a Bússola
 * `enabled_features` id) gates visibility — null means always shown to a
 * logged-in user (the Bússola core screens aren't feature-gated the way
 * the Painel Amparar ones are). */
data class DrawerItem(
    val screen: Screen,
    val labelPtBr: String,
    val featureId: String?,
    val requiresPainelAmparar: Boolean = false,
    val requiresSuperuser: Boolean = false,
)

val DRAWER_ITEMS = listOf(
    DrawerItem(Screen.Dashboard, "Dashboard", featureId = null),
    DrawerItem(Screen.Transactions, "Transações", featureId = null),
    DrawerItem(Screen.Accounts, "Contas", featureId = null),
    DrawerItem(Screen.Tasks, "Tarefas", featureId = "tasks"),
    DrawerItem(Screen.Calendar, "Calendário", featureId = "calendar"),
    DrawerItem(Screen.Carne, "Carnê", featureId = "pa_carne", requiresPainelAmparar = true),
    DrawerItem(Screen.Cobranca, "Cobrança", featureId = "pa_cobranca", requiresPainelAmparar = true),
    DrawerItem(Screen.PainelDashboard, "Dashboard Amparar", featureId = "pa_dashboard", requiresPainelAmparar = true),
    DrawerItem(Screen.Permissions, "Permissões", featureId = null, requiresSuperuser = true),
)
