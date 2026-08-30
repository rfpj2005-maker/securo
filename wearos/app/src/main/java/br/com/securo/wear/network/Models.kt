package br.com.securo.wear.network

import kotlinx.serialization.Serializable

// Mirrors backend/app/schemas/watch_pairing.py.
@Serializable
data class RedeemRequest(val code: String)

@Serializable
data class TokenResponse(val access_token: String, val token_type: String = "bearer")

// Subset of backend/app/schemas/task.py's TaskRead — only the fields the
// watch actually renders. Retrofit/kotlinx.serialization ignore unknown
// JSON keys by default, so trimming fields here is safe even though the
// server sends more (subtasks, timestamps, ids for related rows).
@Serializable
data class TaskDto(
    val id: String,
    val title: String,
    val category: String,
    val due_date: String? = null,
    val due_time: String? = null,
    val status: String,
)

@Serializable
data class TaskStatusUpdate(val status: String)

// Mirrors backend/app/schemas/google_calendar.py.
@Serializable
data class CalendarStatusDto(
    val connected: Boolean,
    val google_email: String? = null,
    val selected_calendar_id: String? = null,
)

@Serializable
data class CalendarEventDto(
    val id: String,
    val summary: String,
    val start: String,
    val end: String,
    val all_day: Boolean,
    val location: String? = null,
)
