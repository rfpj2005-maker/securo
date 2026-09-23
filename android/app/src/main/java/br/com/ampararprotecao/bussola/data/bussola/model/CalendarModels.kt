package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class GoogleCalendarStatus(
    @SerialName("connected") val connected: Boolean,
    @SerialName("google_email") val googleEmail: String? = null,
    @SerialName("selected_calendar_id") val selectedCalendarId: String? = null,
)

@Serializable
data class CalendarEventRead(
    @SerialName("id") val id: String,
    @SerialName("summary") val summary: String,
    @SerialName("description") val description: String? = null,
    @SerialName("location") val location: String? = null,
    // Full ISO datetime ("2026-09-25T14:00:00-03:00") or a plain date
    // ("2026-09-25") when all_day is true.
    @SerialName("start") val start: String,
    @SerialName("end") val end: String,
    @SerialName("all_day") val allDay: Boolean,
    @SerialName("html_link") val htmlLink: String? = null,
    @SerialName("calendar_id") val calendarId: String,
    @SerialName("calendar_summary") val calendarSummary: String? = null,
)

@Serializable
data class CalendarEventCreate(
    @SerialName("summary") val summary: String,
    @SerialName("description") val description: String? = null,
    @SerialName("location") val location: String? = null,
    // Naive local wall-clock ISO ("2026-09-25T14:00:00", no offset) or a
    // plain date when allDay — the backend pairs it with the user's own
    // timezone (see backend/app/services/google_calendar_service.py).
    @SerialName("start") val start: String,
    @SerialName("end") val end: String,
    @SerialName("all_day") val allDay: Boolean = false,
)

/** Always sent as a full replacement, same convention as TaskUpdate. */
@Serializable
data class CalendarEventUpdate(
    @SerialName("summary") val summary: String? = null,
    @SerialName("description") val description: String? = null,
    @SerialName("location") val location: String? = null,
    @SerialName("start") val start: String? = null,
    @SerialName("end") val end: String? = null,
    @SerialName("all_day") val allDay: Boolean? = null,
)
