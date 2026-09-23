package br.com.ampararprotecao.bussola.ui.calendar

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventRead
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale

private val DAY_LABEL_FMT = DateTimeFormatter.ofPattern("d 'de' MMMM", Locale("pt", "BR"))

@Composable
fun CalendarScreen(
    modifier: Modifier = Modifier,
    onAddEvent: () -> Unit,
    onOpenEvent: (String, String) -> Unit,
    viewModel: CalendarViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        modifier = modifier,
        floatingActionButton = {
            if (state.connected) {
                FloatingActionButton(onClick = onAddEvent) {
                    Icon(Icons.Filled.Add, contentDescription = "Novo compromisso")
                }
            }
        },
    ) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            return@Scaffold
        }
        if (!state.connected) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text(
                    "Google Calendar não conectado.\nConecte pelo site do Bússola em Configurações.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(24.dp),
                )
            }
            return@Scaffold
        }
        if (state.events.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Nada agendado nos próximos dias", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            return@Scaffold
        }

        val grouped = state.events
            .sortedBy { it.start }
            .groupBy { it.start.take(10) }

        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(bottom = 88.dp)) {
            grouped.forEach { (dateKey, events) ->
                item(key = "header-$dateKey") {
                    val label = runCatching { LocalDate.parse(dateKey).format(DAY_LABEL_FMT) }.getOrDefault(dateKey)
                    Text(
                        label.replaceFirstChar { it.titlecase(Locale("pt", "BR")) },
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                    )
                }
                items(events, key = { it.id }) { event ->
                    EventRow(event, onClick = { onOpenEvent(event.id, event.calendarId) })
                    HorizontalDivider()
                }
            }
        }
    }
}

@Composable
private fun EventRow(event: CalendarEventRead, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(8.dp).background(Color(0xFFE53935), CircleShape))
        Column(Modifier.padding(start = 12.dp)) {
            Text(event.summary, style = MaterialTheme.typography.bodyLarge)
            val time = if (event.allDay) "Dia inteiro" else event.start.drop(11).take(5)
            val subtitle = if (event.location.isNullOrBlank()) time else "$time · ${event.location}"
            Text(subtitle, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
