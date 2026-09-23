package br.com.ampararprotecao.bussola.ui.tasks

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.Task
import br.com.ampararprotecao.bussola.data.bussola.model.TaskCreate
import br.com.ampararprotecao.bussola.data.bussola.model.TaskUpdate

private val CATEGORIES = listOf("administrative", "management", "commercial", "marketing")
private val CATEGORY_LABELS = mapOf(
    "marketing" to "Marketing",
    "management" to "Gestão",
    "commercial" to "Comercial",
    "administrative" to "Administrativo",
)
private val RECURRENCE_OPTIONS = listOf(null, "daily", "weekly", "monthly", "yearly")
private val RECURRENCE_LABELS = mapOf(
    "daily" to "Diariamente",
    "weekly" to "Semanalmente",
    "monthly" to "Mensalmente",
    "yearly" to "Anualmente",
)
private val RECURRENCE_UNIT = mapOf(
    "daily" to "dia(s)",
    "weekly" to "semana(s)",
    "monthly" to "mês(es)",
    "yearly" to "ano(s)",
)

@Composable
fun TaskEditScreen(
    modifier: Modifier = Modifier,
    taskId: String?,
    onSaved: () -> Unit,
    onDeleted: () -> Unit,
    viewModel: TaskEditViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(taskId) { viewModel.load(taskId) }

    when (val s = state) {
        is TaskEditUiState.Loading -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is TaskEditUiState.Saved -> LaunchedEffect(Unit) { onSaved() }
        is TaskEditUiState.Deleted -> LaunchedEffect(Unit) { onDeleted() }
        is TaskEditUiState.Ready -> TaskEditForm(
            modifier = modifier,
            existing = s,
            taskId = taskId,
            onSave = { create, update -> viewModel.save(taskId, create, update) },
            onDelete = { taskId?.let(viewModel::delete) },
            onAddSubtask = viewModel::addSubtask,
            onToggleSubtask = viewModel::toggleSubtask,
            onDeleteSubtask = viewModel::deleteSubtask,
        )
    }
}

@Composable
private fun TaskEditForm(
    modifier: Modifier,
    existing: TaskEditUiState.Ready,
    taskId: String?,
    onSave: (TaskCreate, TaskUpdate) -> Unit,
    onDelete: () -> Unit,
    onAddSubtask: (String) -> Unit,
    onToggleSubtask: (String, Boolean) -> Unit,
    onDeleteSubtask: (String) -> Unit,
) {
    val task = existing.task
    var title by remember { mutableStateOf(task?.title ?: "") }
    var category by remember { mutableStateOf(task?.category ?: "administrative") }
    var dueDate by remember { mutableStateOf(task?.dueDate ?: "") }
    var dueTime by remember { mutableStateOf(task?.dueTime?.take(5) ?: "") }
    var notes by remember { mutableStateOf(task?.notes ?: "") }
    var recurrence by remember { mutableStateOf(task?.recurrenceFrequency) }
    var recurrenceInterval by remember { mutableStateOf((task?.recurrenceInterval ?: 1).toString()) }
    var recurrenceEndDate by remember { mutableStateOf(task?.recurrenceEndDate ?: "") }
    var newSubtaskTitle by remember { mutableStateOf("") }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        OutlinedTextField(
            value = title,
            onValueChange = { title = it },
            label = { Text("Título") },
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.padding(top = 12.dp))
        Dropdown(
            label = "Categoria",
            options = CATEGORIES,
            optionLabel = { CATEGORY_LABELS[it] ?: it },
            selected = category,
            onSelect = { category = it },
        )

        Spacer(Modifier.padding(top = 12.dp))
        Row {
            OutlinedTextField(
                value = dueDate,
                onValueChange = { dueDate = it },
                label = { Text("Prazo (AAAA-MM-DD)") },
                modifier = Modifier.weight(1f),
            )
            Spacer(Modifier.padding(start = 8.dp))
            OutlinedTextField(
                value = dueTime,
                onValueChange = { dueTime = it },
                label = { Text("Hora (HH:MM)") },
                modifier = Modifier.weight(1f),
            )
        }

        Spacer(Modifier.padding(top = 12.dp))
        Dropdown(
            label = "Repetir",
            options = RECURRENCE_OPTIONS,
            optionLabel = { it?.let { f -> RECURRENCE_LABELS[f] ?: f } ?: "Não repete" },
            selected = recurrence,
            onSelect = { recurrence = it },
        )
        if (dueDate.isBlank()) {
            Text(
                "Defina um prazo pra poder repetir — ideal pra lembrete de remédio.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
        if (recurrence != null && dueDate.isNotBlank()) {
            Spacer(Modifier.padding(top = 8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("A cada", modifier = Modifier.padding(end = 8.dp))
                OutlinedTextField(
                    value = recurrenceInterval,
                    onValueChange = { recurrenceInterval = it.filter { c -> c.isDigit() } },
                    modifier = Modifier.weight(1f),
                )
                Text(RECURRENCE_UNIT[recurrence] ?: "", modifier = Modifier.padding(start = 8.dp))
            }
            Spacer(Modifier.padding(top = 8.dp))
            OutlinedTextField(
                value = recurrenceEndDate,
                onValueChange = { recurrenceEndDate = it },
                label = { Text("Repetir até (opcional, AAAA-MM-DD)") },
                modifier = Modifier.fillMaxWidth(),
            )
        }

        Spacer(Modifier.padding(top = 12.dp))
        OutlinedTextField(
            value = notes,
            onValueChange = { notes = it },
            label = { Text("Observações") },
            modifier = Modifier.fillMaxWidth(),
        )

        if (task != null) {
            Spacer(Modifier.padding(top = 20.dp))
            HorizontalDivider()
            Text("Subtarefas", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(top = 12.dp, bottom = 4.dp))
            task.subtasks.sortedBy { it.position }.forEach { sub ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
                ) {
                    Checkbox(checked = sub.isDone, onCheckedChange = { onToggleSubtask(sub.id, !sub.isDone) })
                    Text(
                        sub.title,
                        modifier = Modifier.weight(1f),
                        textDecoration = if (sub.isDone) TextDecoration.LineThrough else null,
                        color = if (sub.isDone) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface,
                    )
                    IconButton(onClick = { onDeleteSubtask(sub.id) }) {
                        Icon(Icons.Filled.Delete, contentDescription = "Remover subtarefa")
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 4.dp)) {
                OutlinedTextField(
                    value = newSubtaskTitle,
                    onValueChange = { newSubtaskTitle = it },
                    label = { Text("Nova subtarefa") },
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.padding(start = 8.dp))
                Button(onClick = { onAddSubtask(newSubtaskTitle); newSubtaskTitle = "" }, enabled = newSubtaskTitle.isNotBlank()) {
                    Text("Add")
                }
            }
        } else {
            Spacer(Modifier.padding(top = 12.dp))
            Text(
                "Salve a tarefa primeiro para adicionar subtarefas.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        existing.error?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 8.dp))
        }

        Spacer(Modifier.padding(top = 20.dp))
        Button(
            onClick = {
                val recurring = dueDate.isNotBlank() && recurrence != null
                val effectiveRecurrence = if (recurring) recurrence else null
                val effectiveInterval = if (recurring) (recurrenceInterval.toIntOrNull() ?: 1).coerceAtLeast(1) else 1
                val effectiveEndDate = if (recurring) recurrenceEndDate.ifBlank { null } else null
                onSave(
                    TaskCreate(
                        title = title,
                        category = category,
                        dueDate = dueDate.ifBlank { null },
                        dueTime = if (dueDate.isNotBlank()) dueTime.ifBlank { null } else null,
                        notes = notes.ifBlank { null },
                        recurrenceFrequency = effectiveRecurrence,
                        recurrenceInterval = effectiveInterval,
                        recurrenceEndDate = effectiveEndDate,
                    ),
                    TaskUpdate(
                        title = title,
                        category = category,
                        dueDate = dueDate.ifBlank { null },
                        dueTime = if (dueDate.isNotBlank()) dueTime.ifBlank { null } else null,
                        status = task?.status,
                        notes = notes.ifBlank { null },
                        recurrenceFrequency = effectiveRecurrence,
                        recurrenceInterval = effectiveInterval,
                        recurrenceEndDate = effectiveEndDate,
                    ),
                )
            },
            enabled = !existing.saving && title.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (existing.saving) CircularProgressIndicator(Modifier.padding(4.dp), color = MaterialTheme.colorScheme.onPrimary)
            else Text("Salvar")
        }

        if (taskId != null) {
            Spacer(Modifier.padding(top = 8.dp))
            OutlinedButton(onClick = onDelete, modifier = Modifier.fillMaxWidth()) {
                Text("Apagar")
            }
        }
    }
}

@Composable
private fun <T> Dropdown(
    label: String,
    options: List<T>,
    optionLabel: (T) -> String,
    selected: T,
    onSelect: (T) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier = Modifier.fillMaxWidth()) {
        OutlinedTextField(
            value = optionLabel(selected),
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { Icon(Icons.Filled.ArrowDropDown, contentDescription = null) },
            modifier = Modifier
                .fillMaxWidth()
                .clickable { expanded = true },
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(optionLabel(option)) },
                    onClick = { onSelect(option); expanded = false },
                )
            }
        }
    }
}
