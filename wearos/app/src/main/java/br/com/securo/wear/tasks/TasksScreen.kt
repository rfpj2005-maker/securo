package br.com.securo.wear.tasks

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.items
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.CircularProgressIndicator
import androidx.wear.compose.material.ListHeader
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import br.com.securo.wear.R
import br.com.securo.wear.SecuroWearApp
import br.com.securo.wear.network.TaskDto

@Composable
fun TasksScreen() {
    val context = LocalContext.current
    val app = context.applicationContext as SecuroWearApp
    val viewModel: TasksViewModel = viewModel(
        factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                TasksViewModel(app.serverSettings, app.tokenStore) as T
        },
    )
    val state by viewModel.state.collectAsState()

    when (val s = state) {
        TasksUiState.Loading -> CenteredBox { CircularProgressIndicator() }
        TasksUiState.Error -> CenteredBox {
            androidx.compose.foundation.layout.Column(
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(stringResource(R.string.tasks_error), textAlign = TextAlign.Center)
                Button(onClick = { viewModel.refresh() }) {
                    Text(stringResource(R.string.tasks_retry))
                }
            }
        }
        is TasksUiState.Loaded -> {
            if (s.tasks.isEmpty()) {
                CenteredBox { Text(stringResource(R.string.tasks_empty), textAlign = TextAlign.Center) }
            } else {
                ScalingLazyColumn(modifier = Modifier.fillMaxSize()) {
                    item { ListHeader { Text(stringResource(R.string.tasks_title)) } }
                    items(s.tasks) { task -> TaskRow(task = task, onComplete = { viewModel.complete(task) }) }
                }
            }
        }
    }
}

@Composable
private fun TaskRow(task: TaskDto, onComplete: () -> Unit) {
    Chip(
        onClick = onComplete,
        label = { Text(task.title, maxLines = 2) },
        secondaryLabel = dueLabel(task)?.let { { Text(it) } },
        colors = ChipDefaults.secondaryChipColors(),
        modifier = Modifier.padding(vertical = 2.dp),
    )
}

private fun dueLabel(task: TaskDto): String? {
    val date = task.due_date ?: return null
    return if (task.due_time != null) "$date ${task.due_time}" else date
}

@Composable
private fun CenteredBox(content: @Composable () -> Unit) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { content() }
}
