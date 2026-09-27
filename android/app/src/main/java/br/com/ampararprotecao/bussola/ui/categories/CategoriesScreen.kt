package br.com.ampararprotecao.bussola.ui.categories

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.CategoryGroup

@Composable
fun CategoriesScreen(modifier: Modifier = Modifier, viewModel: CategoriesViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var editing by remember { mutableStateOf<Category?>(null) }
    var creating by remember { mutableStateOf(false) }

    Scaffold(
        modifier = modifier,
        floatingActionButton = {
            FloatingActionButton(onClick = { creating = true }) {
                Icon(Icons.Filled.Add, contentDescription = "Nova categoria")
            }
        },
    ) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            return@Scaffold
        }

        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(bottom = 88.dp)) {
            state.groups.forEach { group ->
                if (group.categories.isEmpty()) return@forEach
                item(key = "hdr-${group.id}") { GroupHeader(group.name, group.color) }
                items(group.categories, key = { it.id }) { cat ->
                    CategoryRow(cat, onClick = { editing = cat })
                    HorizontalDivider()
                }
            }
            if (state.ungrouped.isNotEmpty()) {
                item(key = "hdr-none") { GroupHeader("Sem grupo", "#6B7280") }
                items(state.ungrouped, key = { it.id }) { cat ->
                    CategoryRow(cat, onClick = { editing = cat })
                    HorizontalDivider()
                }
            }
        }
    }

    val allGroups = state.groups
    if (editing != null) {
        CategoryEditDialog(
            category = editing,
            groups = allGroups,
            onDismiss = { editing = null },
            onSave = { name, color, groupId -> viewModel.save(editing!!.id, name, color, groupId) { editing = null } },
            onDelete = { viewModel.delete(editing!!.id) { editing = null } },
        )
    }
    if (creating) {
        CategoryEditDialog(
            category = null,
            groups = allGroups,
            onDismiss = { creating = false },
            onSave = { name, color, groupId -> viewModel.save(null, name, color, groupId) { creating = false } },
            onDelete = null,
        )
    }
}

@Composable
private fun GroupHeader(name: String, colorHex: String) {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(parseColor(colorHex)))
        Text(
            name.uppercase(),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 8.dp),
        )
    }
}

@Composable
private fun CategoryRow(category: Category, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(14.dp).clip(CircleShape).background(parseColor(category.color)))
        Text(category.name, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(start = 12.dp))
    }
}

@Composable
private fun CategoryEditDialog(
    category: Category?,
    groups: List<CategoryGroup>,
    onDismiss: () -> Unit,
    onSave: (name: String, color: String, groupId: String?) -> Unit,
    onDelete: (() -> Unit)?,
) {
    var name by remember { mutableStateOf(category?.name ?: "") }
    var color by remember { mutableStateOf(category?.color ?: CATEGORY_COLOR_SWATCHES.first()) }
    var groupId by remember { mutableStateOf(category?.groupId) }
    var groupMenuExpanded by remember { mutableStateOf(false) }
    var confirmingDelete by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (category == null) "Nova categoria" else "Editar categoria") },
        text = {
            Column {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nome") }, modifier = Modifier.fillMaxWidth())

                Text("Cor", style = MaterialTheme.typography.labelMedium, modifier = Modifier.padding(top = 16.dp, bottom = 6.dp))
                ColorSwatchGrid(selected = color, onSelect = { color = it })

                Text("Grupo", style = MaterialTheme.typography.labelMedium, modifier = Modifier.padding(top = 16.dp, bottom = 6.dp))
                Box {
                    OutlinedTextField(
                        value = groups.find { it.id == groupId }?.name ?: "Sem grupo",
                        onValueChange = {},
                        readOnly = true,
                        trailingIcon = { Icon(Icons.Filled.ExpandMore, contentDescription = null) },
                        modifier = Modifier.fillMaxWidth().clickable { groupMenuExpanded = true },
                        enabled = false,
                    )
                    DropdownMenu(expanded = groupMenuExpanded, onDismissRequest = { groupMenuExpanded = false }) {
                        DropdownMenuItem(text = { Text("Sem grupo") }, onClick = { groupId = null; groupMenuExpanded = false })
                        groups.forEach { g ->
                            DropdownMenuItem(text = { Text(g.name) }, onClick = { groupId = g.id; groupMenuExpanded = false })
                        }
                    }
                }

                if (onDelete != null) {
                    if (confirmingDelete) {
                        Row(Modifier.padding(top = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Apagar essa categoria?", style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                            TextButton(onClick = onDelete) { Text("Apagar", color = MaterialTheme.colorScheme.error) }
                        }
                    } else {
                        TextButton(onClick = { confirmingDelete = true }, modifier = Modifier.padding(top = 12.dp)) {
                            Icon(Icons.Filled.Delete, contentDescription = null, modifier = Modifier.size(16.dp))
                            Text("Apagar", modifier = Modifier.padding(start = 6.dp))
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { onSave(name, color, groupId) }, enabled = name.isNotBlank()) { Text("Salvar") }
        },
        dismissButton = { OutlinedButton(onClick = onDismiss) { Text("Cancelar") } },
    )
}

@Composable
private fun ColorSwatchGrid(selected: String, onSelect: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        CATEGORY_COLOR_SWATCHES.chunked(7).forEach { rowColors ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                rowColors.forEach { hex ->
                    val isSelected = hex.equals(selected, ignoreCase = true)
                    Box(
                        Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .background(parseColor(hex))
                            .clickable { onSelect(hex) },
                        contentAlignment = Alignment.Center,
                    ) {
                        if (isSelected) Icon(Icons.Filled.Check, contentDescription = null, tint = Color.White, modifier = Modifier.size(16.dp))
                    }
                }
            }
        }
    }
}

private fun parseColor(hex: String?): Color = runCatching {
    Color(android.graphics.Color.parseColor(hex))
}.getOrDefault(Color.Gray)
