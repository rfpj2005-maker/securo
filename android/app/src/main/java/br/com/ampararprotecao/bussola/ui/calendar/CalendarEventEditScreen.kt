package br.com.ampararprotecao.bussola.ui.calendar

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventCreate
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventUpdate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

private val DEFAULT_TIME_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm")

@Composable
fun CalendarEventEditScreen(
    modifier: Modifier = Modifier,
    eventId: String?,
    calendarId: String?,
    onSaved: () -> Unit,
    onDeleted: () -> Unit,
    viewModel: CalendarEventEditViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(eventId) { viewModel.load(eventId, calendarId) }

    when (val s = state) {
        is CalendarEventEditUiState.Loading -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is CalendarEventEditUiState.Saved -> LaunchedEffect(Unit) { onSaved() }
        is CalendarEventEditUiState.Deleted -> LaunchedEffect(Unit) { onDeleted() }
        is CalendarEventEditUiState.Ready -> CalendarEventEditForm(
            modifier = modifier,
            existing = s,
            eventId = eventId,
            calendarId = calendarId ?: s.event?.calendarId,
            onSave = { create, update -> viewModel.save(eventId, calendarId ?: s.event?.calendarId, create, update) },
            onDelete = {
                val id = eventId ?: return@CalendarEventEditForm
                val calId = calendarId ?: s.event?.calendarId ?: return@CalendarEventEditForm
                viewModel.delete(id, calId)
            },
        )
    }
}

@Composable
private fun CalendarEventEditForm(
    modifier: Modifier,
    existing: CalendarEventEditUiState.Ready,
    eventId: String?,
    calendarId: String?,
    onSave: (CalendarEventCreate, CalendarEventUpdate) -> Unit,
    onDelete: () -> Unit,
) {
    val event = existing.event
    var summary by remember { mutableStateOf(event?.summary ?: "") }
    var description by remember { mutableStateOf(event?.description ?: "") }
    var location by remember { mutableStateOf(event?.location ?: "") }
    var allDay by remember { mutableStateOf(event?.allDay ?: false) }
    var endFollowsStart by remember { mutableStateOf(event == null) }

    val defaultStart = remember { LocalDateTime.now().withMinute(0).plusHours(1).format(DEFAULT_TIME_FMT) }
    var start by remember { mutableStateOf(event?.start?.take(if (event.allDay) 10 else 16) ?: defaultStart) }
    var end by remember {
        mutableStateOf(
            event?.end?.take(if (event.allDay) 10 else 16)
                ?: LocalDateTime.now().withMinute(0).plusHours(2).format(DEFAULT_TIME_FMT),
        )
    }

    fun onStartChange(value: String) {
        start = value
        if (event == null && endFollowsStart) {
            end = if (allDay) value else {
                runCatching { LocalDateTime.parse(value, DEFAULT_TIME_FMT).plusHours(1).format(DEFAULT_TIME_FMT) }
                    .getOrDefault(end)
            }
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        OutlinedTextField(
            value = summary,
            onValueChange = { summary = it },
            label = { Text("Título") },
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.padding(top = 12.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked = allDay, onCheckedChange = { allDay = it })
            Text("Dia inteiro")
        }
        Spacer(Modifier.padding(top = 4.dp))
        Row {
            OutlinedTextField(
                value = start,
                onValueChange = ::onStartChange,
                label = { Text(if (allDay) "Início (AAAA-MM-DD)" else "Início (AAAA-MM-DDTHH:MM)") },
                modifier = Modifier.weight(1f),
            )
            Spacer(Modifier.padding(start = 8.dp))
            OutlinedTextField(
                value = end,
                onValueChange = { end = it; endFollowsStart = false },
                label = { Text(if (allDay) "Fim (AAAA-MM-DD)" else "Fim (AAAA-MM-DDTHH:MM)") },
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = location,
            onValueChange = { location = it },
            label = { Text("Local") },
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = description,
            onValueChange = { description = it },
            label = { Text("Descrição") },
            modifier = Modifier.fillMaxWidth(),
        )

        existing.error?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp))
        }

        Spacer(Modifier.padding(top = 20.dp))
        Button(
            onClick = {
                val startValue = if (allDay) start else if (start.length == 16) "$start:00" else start
                val endValue = if (allDay) end else if (end.length == 16) "$end:00" else end
                onSave(
                    CalendarEventCreate(
                        summary = summary,
                        description = description.ifBlank { null },
                        location = location.ifBlank { null },
                        start = startValue,
                        end = endValue,
                        allDay = allDay,
                    ),
                    CalendarEventUpdate(
                        summary = summary,
                        description = description.ifBlank { null },
                        location = location.ifBlank { null },
                        start = startValue,
                        end = endValue,
                        allDay = allDay,
                    ),
                )
            },
            enabled = !existing.saving && summary.isNotBlank() && start.isNotBlank() && end.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (existing.saving) CircularProgressIndicator(Modifier.padding(4.dp), color = MaterialTheme.colorScheme.onPrimary)
            else Text("Salvar")
        }

        if (eventId != null && calendarId != null) {
            Spacer(Modifier.padding(top = 8.dp))
            OutlinedButton(onClick = onDelete, modifier = Modifier.fillMaxWidth()) {
                Text("Apagar")
            }
        }
    }
}
