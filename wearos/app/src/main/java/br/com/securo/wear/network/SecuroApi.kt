package br.com.securo.wear.network

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.Path
import retrofit2.http.Query

/** Only the endpoints Phase 1 (pairing + Tasks + Calendar) needs. Add to
 *  this as later phases (Siprov voice, general chat, meeting recording)
 *  land — see backend/app/agents/api/chat.py and app/api/meetings.py. */
interface SecuroApi {
    // Unauthenticated — this is how the watch gets its token in the
    // first place. See backend/app/api/watch_pairing.py.
    @retrofit2.http.POST("api/auth/watch-pair/redeem")
    suspend fun redeemWatchPairing(@Body body: RedeemRequest): Response<TokenResponse>

    @GET("api/tasks")
    suspend fun listTasks(@Query("status") status: String? = "pending"): Response<List<TaskDto>>

    @PATCH("api/tasks/{id}")
    suspend fun updateTaskStatus(
        @Path("id") id: String,
        @Body body: TaskStatusUpdate,
    ): Response<TaskDto>

    @GET("api/integrations/google-calendar/status")
    suspend fun calendarStatus(): Response<CalendarStatusDto>

    @GET("api/integrations/google-calendar/events")
    suspend fun listCalendarEvents(
        @Query("start") start: String,
        @Query("end") end: String,
    ): Response<List<CalendarEventDto>>
}
