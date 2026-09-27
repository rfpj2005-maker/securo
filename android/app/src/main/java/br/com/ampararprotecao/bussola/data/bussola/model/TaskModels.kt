package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Subtask(
    @SerialName("id") val id: String,
    @SerialName("task_id") val taskId: String,
    @SerialName("title") val title: String,
    @SerialName("is_done") val isDone: Boolean,
    @SerialName("position") val position: Int,
)

@Serializable
data class Task(
    @SerialName("id") val id: String,
    @SerialName("user_id") val userId: String,
    @SerialName("title") val title: String,
    @SerialName("category") val category: String,
    @SerialName("due_date") val dueDate: String? = null,
    @SerialName("due_time") val dueTime: String? = null,
    @SerialName("status") val status: String,
    @SerialName("notes") val notes: String? = null,
    @SerialName("source_meeting_id") val sourceMeetingId: String? = null,
    // Nullable — recurrence_frequency: null means "does not repeat" (see
    // backend/app/schemas/task.py).
    @SerialName("recurrence_frequency") val recurrenceFrequency: String? = null,
    @SerialName("recurrence_interval") val recurrenceInterval: Int = 1,
    @SerialName("recurrence_end_date") val recurrenceEndDate: String? = null,
    @SerialName("subtasks") val subtasks: List<Subtask> = emptyList(),
)

@Serializable
data class TaskCreate(
    @SerialName("title") val title: String,
    @SerialName("category") val category: String = "administrative",
    @SerialName("due_date") val dueDate: String? = null,
    @SerialName("due_time") val dueTime: String? = null,
    @SerialName("status") val status: String = "pending",
    @SerialName("notes") val notes: String? = null,
    @SerialName("recurrence_frequency") val recurrenceFrequency: String? = null,
    @SerialName("recurrence_interval") val recurrenceInterval: Int = 1,
    @SerialName("recurrence_end_date") val recurrenceEndDate: String? = null,
)

/** Always sent as a full replacement (every field), never a true partial
 * patch — same convention as TransactionEditPayload. Simpler than tracking
 * per-field "was this touched" state, and the backend's PATCH accepts a
 * full body fine (it just diffs against exclude_unset, which "all fields
 * present" satisfies trivially). */
@Serializable
data class TaskUpdate(
    @SerialName("title") val title: String? = null,
    @SerialName("category") val category: String? = null,
    @SerialName("due_date") val dueDate: String? = null,
    @SerialName("due_time") val dueTime: String? = null,
    @SerialName("status") val status: String? = null,
    @SerialName("notes") val notes: String? = null,
    @SerialName("recurrence_frequency") val recurrenceFrequency: String? = null,
    @SerialName("recurrence_interval") val recurrenceInterval: Int? = null,
    @SerialName("recurrence_end_date") val recurrenceEndDate: String? = null,
)

@Serializable
data class SubtaskCreate(@SerialName("title") val title: String)

@Serializable
data class SubtaskUpdate(
    @SerialName("title") val title: String? = null,
    @SerialName("is_done") val isDone: Boolean? = null,
)
