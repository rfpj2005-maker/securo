package br.com.ampararprotecao.bussola.ui.goals

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.Goal
import br.com.ampararprotecao.bussola.ui.theme.PrimaryDark

@Composable
fun GoalsScreen(modifier: Modifier = Modifier, viewModel: GoalsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var editing by remember { mutableStateOf<Goal?>(null) }
    var creating by remember { mutableStateOf(false) }

    Scaffold(
        modifier = modifier,
        floatingActionButton = {
            FloatingActionButton(onClick = { creating = true }) { Icon(Icons.Filled.Add, contentDescription = "Nova meta") }
        },
    ) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            return@Scaffold
        }
        if (state.goals.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Nenhuma meta ainda", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            return@Scaffold
        }
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(bottom = 88.dp)) {
            items(state.goals, key = { it.id }) { goal ->
                GoalRow(goal, onClick = { editing = goal })
                HorizontalDivider()
            }
        }
    }

    if (editing != null || creating) {
        GoalEditDialog(
            goal = editing,
            onDismiss = { editing = null; creating = false },
            onSave = { name, target, current, date ->
                viewModel.save(editing?.id, name, target, current, date) { editing = null; creating = false }
            },
            onDelete = editing?.let { g -> { viewModel.delete(g.id) { editing = null } } },
        )
    }
}

@Composable
private fun GoalRow(goal: Goal, onClick: () -> Unit) {
    val target = goal.targetAmount.toDoubleOrNull() ?: 0.0
    val current = goal.currentAmount.toDoubleOrNull() ?: 0.0
    val pct = if (target > 0) (current / target).coerceIn(0.0, 1.0) else 0.0

    Column(
        Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 10.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(goal.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text("${(pct * 100).toInt()}%", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(
            "R$ ${"%.2f".format(current)} de R$ ${"%.2f".format(target)}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Box(
            Modifier.padding(top = 6.dp).fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)).background(MaterialTheme.colorScheme.surfaceVariant),
        ) {
            Box(Modifier.fillMaxWidth(pct.toFloat()).height(6.dp).clip(RoundedCornerShape(3.dp)).background(PrimaryDark))
        }
    }
}

@Composable
private fun GoalEditDialog(
    goal: Goal?,
    onDismiss: () -> Unit,
    onSave: (name: String, target: String, current: String, date: String?) -> Unit,
    onDelete: (() -> Unit)?,
) {
    var name by remember { mutableStateOf(goal?.name ?: "") }
    var target by remember { mutableStateOf(goal?.targetAmount ?: "") }
    var current by remember { mutableStateOf(goal?.currentAmount ?: "0") }
    var date by remember { mutableStateOf(goal?.targetDate ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (goal == null) "Nova meta" else "Editar meta") },
        text = {
            Column {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nome") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(
                    value = target,
                    onValueChange = { target = it },
                    label = { Text("Valor da meta (R$)") },
                    modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                )
                OutlinedTextField(
                    value = current,
                    onValueChange = { current = it },
                    label = { Text("Valor atual (R$)") },
                    modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                )
                OutlinedTextField(
                    value = date,
                    onValueChange = { date = it },
                    label = { Text("Prazo (AAAA-MM-DD, opcional)") },
                    modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                )
                if (onDelete != null) {
                    TextButton(onClick = onDelete, modifier = Modifier.padding(top = 8.dp)) {
                        Text("Apagar meta", color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onSave(name, target, current, date.ifBlank { null }) },
                enabled = name.isNotBlank() && target.toDoubleOrNull() != null,
            ) { Text("Salvar") }
        },
        dismissButton = { OutlinedButton(onClick = onDismiss) { Text("Cancelar") } },
    )
}
