package br.com.ampararprotecao.bussola.data.bussola.api

import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.Budget
import br.com.ampararprotecao.bussola.data.bussola.model.BudgetCreate
import br.com.ampararprotecao.bussola.data.bussola.model.BudgetUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.BudgetVsActual
import br.com.ampararprotecao.bussola.data.bussola.model.Camera
import br.com.ampararprotecao.bussola.data.bussola.model.CameraRecording
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventCreate
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventRead
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.CategoryCreate
import br.com.ampararprotecao.bussola.data.bussola.model.CategoryGroup
import br.com.ampararprotecao.bussola.data.bussola.model.CategoryUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.DashboardSummary
import br.com.ampararprotecao.bussola.data.bussola.model.Goal
import br.com.ampararprotecao.bussola.data.bussola.model.GoalCreate
import br.com.ampararprotecao.bussola.data.bussola.model.GoalUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.GoogleCalendarStatus
import br.com.ampararprotecao.bussola.data.bussola.model.LoginResponse
import br.com.ampararprotecao.bussola.data.bussola.model.MemberModulesUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.PaginatedTransactions
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransaction
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransactionCreate
import br.com.ampararprotecao.bussola.data.bussola.model.RecurringTransactionUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.SpendingByCategory
import br.com.ampararprotecao.bussola.data.bussola.model.Subtask
import br.com.ampararprotecao.bussola.data.bussola.model.SubtaskCreate
import br.com.ampararprotecao.bussola.data.bussola.model.SubtaskUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.Task
import br.com.ampararprotecao.bussola.data.bussola.model.TaskCreate
import br.com.ampararprotecao.bussola.data.bussola.model.TaskUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.Transaction
import br.com.ampararprotecao.bussola.data.bussola.model.TransactionEditPayload
import br.com.ampararprotecao.bussola.data.bussola.model.TwoFactorVerifyRequest
import br.com.ampararprotecao.bussola.data.bussola.model.UserRead
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceMember
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceRead
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

interface BussolaAuthApi {
    // OAuth2PasswordRequestForm on the backend — form-urlencoded, not JSON.
    @FormUrlEncoded
    @POST("auth/login")
    suspend fun login(@Field("username") username: String, @Field("password") password: String): LoginResponse

    @POST("auth/2fa/verify")
    suspend fun verifyTwoFactor(@Body body: TwoFactorVerifyRequest): LoginResponse

    @GET("users/me")
    suspend fun me(): UserRead
}

interface BussolaWorkspacesApi {
    @GET("workspaces")
    suspend fun list(): List<WorkspaceRead>

    @GET("workspaces/{id}/members")
    suspend fun members(@Path("id") workspaceId: String): List<WorkspaceMember>

    @PUT("workspaces/{id}/members/{userId}/modules")
    suspend fun setMemberModules(
        @Path("id") workspaceId: String,
        @Path("userId") userId: String,
        @Body body: MemberModulesUpdate,
    ): MemberModulesUpdate
}

interface BussolaDashboardApi {
    @GET("dashboard/summary")
    suspend fun summary(@Query("month") month: String? = null): DashboardSummary

    @GET("dashboard/spending-by-category")
    suspend fun spendingByCategory(@Query("month") month: String? = null): List<SpendingByCategory>
}

interface BussolaTransactionsApi {
    @GET("transactions")
    suspend fun list(
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 30,
        @Query("q") query: String? = null,
        @Query("account_id") accountId: String? = null,
        @Query("category_id") categoryId: String? = null,
        @Query("from") from: String? = null,
        @Query("to") to: String? = null,
        @Query("sort_by") sortBy: String? = null,
        @Query("sort_dir") sortDir: String? = null,
    ): PaginatedTransactions

    @GET("transactions/{id}")
    suspend fun get(@Path("id") id: String): Transaction

    @POST("transactions")
    suspend fun create(@Body body: TransactionEditPayload): Transaction

    @PATCH("transactions/{id}")
    suspend fun update(@Path("id") id: String, @Body body: TransactionEditPayload): Transaction

    @DELETE("transactions/{id}")
    suspend fun delete(@Path("id") id: String)
}

interface BussolaCategoriesApi {
    @GET("categories")
    suspend fun list(): List<Category>

    @POST("categories")
    suspend fun create(@Body body: CategoryCreate): Category

    @PATCH("categories/{id}")
    suspend fun update(@Path("id") id: String, @Body body: CategoryUpdate): Category

    @DELETE("categories/{id}")
    suspend fun delete(@Path("id") id: String)

    @GET("category-groups")
    suspend fun groups(): List<CategoryGroup>
}

interface BussolaBudgetsApi {
    @GET("budgets")
    suspend fun list(@Query("month") month: String? = null): List<Budget>

    @GET("budgets/comparison")
    suspend fun comparison(@Query("month") month: String? = null): List<BudgetVsActual>

    @POST("budgets")
    suspend fun create(@Body body: BudgetCreate): Budget

    @PATCH("budgets/{id}")
    suspend fun update(@Path("id") id: String, @Body body: BudgetUpdate): Budget

    @DELETE("budgets/{id}")
    suspend fun delete(@Path("id") id: String)
}

interface BussolaGoalsApi {
    @GET("goals")
    suspend fun list(): List<Goal>

    @POST("goals")
    suspend fun create(@Body body: GoalCreate): Goal

    @PATCH("goals/{id}")
    suspend fun update(@Path("id") id: String, @Body body: GoalUpdate): Goal

    @DELETE("goals/{id}")
    suspend fun delete(@Path("id") id: String)
}

interface BussolaRecurringApi {
    @GET("recurring-transactions")
    suspend fun list(): List<RecurringTransaction>

    @POST("recurring-transactions")
    suspend fun create(@Body body: RecurringTransactionCreate): RecurringTransaction

    @PATCH("recurring-transactions/{id}")
    suspend fun update(@Path("id") id: String, @Body body: RecurringTransactionUpdate): RecurringTransaction

    @DELETE("recurring-transactions/{id}")
    suspend fun delete(@Path("id") id: String)
}

interface BussolaAccountsApi {
    @GET("accounts")
    suspend fun list(@Query("include_closed") includeClosed: Boolean = false): List<Account>
}

interface BussolaTasksApi {
    @GET("tasks")
    suspend fun list(
        @Query("category") category: String? = null,
        @Query("status") status: String? = null,
    ): List<Task>

    @GET("tasks/{id}")
    suspend fun get(@Path("id") id: String): Task

    @POST("tasks")
    suspend fun create(@Body body: TaskCreate): Task

    @PATCH("tasks/{id}")
    suspend fun update(@Path("id") id: String, @Body body: TaskUpdate): Task

    @DELETE("tasks/{id}")
    suspend fun delete(@Path("id") id: String)

    @POST("tasks/{taskId}/subtasks")
    suspend fun createSubtask(@Path("taskId") taskId: String, @Body body: SubtaskCreate): Subtask

    @PATCH("tasks/{taskId}/subtasks/{subtaskId}")
    suspend fun updateSubtask(
        @Path("taskId") taskId: String,
        @Path("subtaskId") subtaskId: String,
        @Body body: SubtaskUpdate,
    ): Subtask

    @DELETE("tasks/{taskId}/subtasks/{subtaskId}")
    suspend fun deleteSubtask(@Path("taskId") taskId: String, @Path("subtaskId") subtaskId: String)
}

interface BussolaCalendarApi {
    @GET("integrations/google-calendar/status")
    suspend fun status(): GoogleCalendarStatus

    @GET("integrations/google-calendar/events")
    suspend fun events(
        @Query("start") start: String? = null,
        @Query("end") end: String? = null,
    ): List<CalendarEventRead>

    @POST("integrations/google-calendar/events")
    suspend fun createEvent(@Body body: CalendarEventCreate): CalendarEventRead

    @PATCH("integrations/google-calendar/events/{id}")
    suspend fun updateEvent(
        @Path("id") id: String,
        @Query("calendar_id") calendarId: String,
        @Body body: CalendarEventUpdate,
    ): CalendarEventRead

    @DELETE("integrations/google-calendar/events/{id}")
    suspend fun deleteEvent(@Path("id") id: String, @Query("calendar_id") calendarId: String)
}

interface BussolaCamerasApi {
    @GET("cameras")
    suspend fun list(): List<Camera>

    @retrofit2.http.Streaming
    @GET("cameras/snapshot/{location}/{cameraId}")
    suspend fun snapshot(@Path("location") location: String, @Path("cameraId") cameraId: Int): ResponseBody

    @GET("cameras/recordings/{location}/{cameraName}")
    suspend fun recordings(@Path("location") location: String, @Path("cameraName") cameraName: String): List<CameraRecording>

    @GET("cameras/search/{location}/{cameraName}")
    suspend fun search(
        @Path("location") location: String,
        @Path("cameraName") cameraName: String,
        @Query("date") date: String? = null,
        @Query("time_from") timeFrom: String? = null,
        @Query("time_to") timeTo: String? = null,
    ): List<CameraRecording>

    @retrofit2.http.Streaming
    @GET("cameras/recording/{location}/{cameraName}/{filename}")
    suspend fun recording(
        @Path("location") location: String,
        @Path("cameraName") cameraName: String,
        @Path("filename") filename: String,
    ): ResponseBody
}
