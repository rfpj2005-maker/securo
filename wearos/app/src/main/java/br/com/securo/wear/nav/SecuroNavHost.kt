package br.com.securo.wear.nav

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.ListHeader
import androidx.wear.compose.material.Text
import androidx.wear.compose.navigation.SwipeDismissableNavHost
import androidx.wear.compose.navigation.composable
import androidx.wear.compose.navigation.rememberSwipeDismissableNavController
import br.com.securo.wear.R
import br.com.securo.wear.calendar.CalendarScreen
import br.com.securo.wear.pairing.PairingScreen
import br.com.securo.wear.tasks.TasksScreen

private object Routes {
    const val PAIRING = "pairing"
    const val HOME = "home"
    const val TASKS = "tasks"
    const val CALENDAR = "calendar"
}

@Composable
fun SecuroNavHost(isPaired: Boolean) {
    val navController = rememberSwipeDismissableNavController()
    SwipeDismissableNavHost(
        navController = navController,
        startDestination = if (isPaired) Routes.HOME else Routes.PAIRING,
    ) {
        composable(Routes.PAIRING) {
            PairingScreen(
                onPaired = {
                    navController.navigate(Routes.HOME) {
                        popUpTo(Routes.PAIRING) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.HOME) {
            HomeMenu(
                onTasks = { navController.navigate(Routes.TASKS) },
                onCalendar = { navController.navigate(Routes.CALENDAR) },
            )
        }
        composable(Routes.TASKS) { TasksScreen() }
        composable(Routes.CALENDAR) { CalendarScreen() }
    }
}

@Composable
private fun HomeMenu(onTasks: () -> Unit, onCalendar: () -> Unit) {
    ScalingLazyColumn(modifier = Modifier.fillMaxSize()) {
        item { ListHeader { Text(stringResource(R.string.app_name)) } }
        item {
            Chip(
                onClick = onTasks,
                label = { Text(stringResource(R.string.nav_tasks)) },
                colors = ChipDefaults.primaryChipColors(),
            )
        }
        item {
            Chip(
                onClick = onCalendar,
                label = { Text(stringResource(R.string.nav_calendar)) },
                colors = ChipDefaults.primaryChipColors(),
            )
        }
    }
}
