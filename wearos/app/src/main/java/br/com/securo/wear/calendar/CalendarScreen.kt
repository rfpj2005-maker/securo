package br.com.securo.wear.calendar

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.CircularProgressIndicator
import androidx.wear.compose.material.ListHeader
import androidx.wear.compose.material.Text
import br.com.securo.wear.R
import br.com.securo.wear.SecuroWearApp
import br.com.securo.wear.network.CalendarEventDto
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException

@Composable
fun CalendarScreen() {
    val context = LocalContext.current
    val app = context.applicationContext as SecuroWearApp
    val viewModel: CalendarViewModel = viewModel(
        factory = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                CalendarViewModel(app.serverSettings, app.tokenStore) as T
        },
    )
    val state by viewModel.state.collectAsState()

    when (val s = state) {
        CalendarUiState.Loading -> CenteredBox { CircularProgressIndicator() }
        CalendarUiState.Error -> CenteredBox {
            Text(stringResource(R.string.calendar_error), textAlign = TextAlign.Center)
        }
        CalendarUiState.NotConnected -> CenteredBox {
            Text(
                stringResource(R.string.calendar_not_connected),
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 12.dp),
            )
        }
        is CalendarUiState.Loaded -> {
            if (s.events.isEmpty()) {
                CenteredBox { Text(stringResource(R.string.calendar_empty), textAlign = TextAlign.Center) }
            } else {
                ScalingLazyColumn(modifier = Modifier.fillMaxSize()) {
                    item { ListHeader { Text(stringResource(R.string.calendar_title)) } }
                    items(s.events) { event -> EventRow(event) }
                }
            }
        }
    }
}

@Composable
private fun EventRow(event: CalendarEventDto) {
    Chip(
        onClick = {},
        label = { Text(event.summary, maxLines = 2) },
        secondaryLabel = { Text(formatEventTime(event)) },
        colors = ChipDefaults.secondaryChipColors(),
        modifier = Modifier.padding(vertical = 2.dp),
    )
}

private val TIME_FORMATTER: DateTimeFormatter = DateTimeFormatter.ofPattern("dd/MM HH:mm")

private fun formatEventTime(event: CalendarEventDto): String {
    if (event.all_day) return event.start.substring(0, minOf(10, event.start.length))
    return try {
        OffsetDateTime.parse(event.start).format(TIME_FORMATTER)
    } catch (e: DateTimeParseException) {
        event.start
    }
}

@Composable
private fun CenteredBox(content: @Composable () -> Unit) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { content() }
}
