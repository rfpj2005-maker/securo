package br.com.ampararprotecao.bussola.data.bussola.repository

import br.com.ampararprotecao.bussola.data.BussolaTokenStore
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaAccountsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaBudgetsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCalendarApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCamerasApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCategoriesApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaDashboardApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaGoalsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaRecurringApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaTasksApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaTransactionsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaWorkspacesApi
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
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceMember
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceRead
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BussolaDashboardRepository @Inject constructor(private val api: BussolaDashboardApi) {
    suspend fun summary(month: String? = null): DashboardSummary = api.summary(month)
    suspend fun spendingByCategory(month: String? = null): List<SpendingByCategory> = api.spendingByCategory(month)
}

@Singleton
class BussolaTransactionsRepository @Inject constructor(private val api: BussolaTransactionsApi) {
    suspend fun list(
        page: Int = 1,
        limit: Int = 30,
        query: String? = null,
        accountId: String? = null,
        categoryId: String? = null,
        from: String? = null,
        to: String? = null,
        sortBy: String? = null,
        sortDir: String? = null,
    ): PaginatedTransactions = api.list(page, limit, query, accountId, categoryId, from, to, sortBy, sortDir)

    suspend fun recent(limit: Int = 10): List<Transaction> =
        api.list(page = 1, limit = limit, sortBy = "date", sortDir = "desc").items

    suspend fun get(id: String): Transaction = api.get(id)
    suspend fun create(payload: TransactionEditPayload): Transaction = api.create(payload)
    suspend fun update(id: String, payload: TransactionEditPayload): Transaction = api.update(id, payload)
    suspend fun delete(id: String) = api.delete(id)
}

@Singleton
class BussolaCategoriesRepository @Inject constructor(private val api: BussolaCategoriesApi) {
    suspend fun list(): List<Category> = api.list()
    suspend fun groups(): List<CategoryGroup> = api.groups()
    suspend fun create(body: CategoryCreate): Category = api.create(body)
    suspend fun update(id: String, body: CategoryUpdate): Category = api.update(id, body)
    suspend fun delete(id: String) = api.delete(id)
}

@Singleton
class BussolaBudgetsRepository @Inject constructor(private val api: BussolaBudgetsApi) {
    suspend fun list(month: String? = null): List<Budget> = api.list(month)
    suspend fun comparison(month: String? = null): List<BudgetVsActual> = api.comparison(month)
    suspend fun create(body: BudgetCreate): Budget = api.create(body)
    suspend fun update(id: String, body: BudgetUpdate): Budget = api.update(id, body)
    suspend fun delete(id: String) = api.delete(id)
}

@Singleton
class BussolaGoalsRepository @Inject constructor(private val api: BussolaGoalsApi) {
    suspend fun list(): List<Goal> = api.list()
    suspend fun create(body: GoalCreate): Goal = api.create(body)
    suspend fun update(id: String, body: GoalUpdate): Goal = api.update(id, body)
    suspend fun delete(id: String) = api.delete(id)
}

@Singleton
class BussolaRecurringRepository @Inject constructor(private val api: BussolaRecurringApi) {
    suspend fun list(): List<RecurringTransaction> = api.list()
    suspend fun create(body: RecurringTransactionCreate): RecurringTransaction = api.create(body)
    suspend fun update(id: String, body: RecurringTransactionUpdate): RecurringTransaction = api.update(id, body)
    suspend fun delete(id: String) = api.delete(id)
}

@Singleton
class BussolaAccountsRepository @Inject constructor(private val api: BussolaAccountsApi) {
    suspend fun list(includeClosed: Boolean = false): List<Account> = api.list(includeClosed)
}

@Singleton
class BussolaWorkspacesRepository @Inject constructor(
    private val api: BussolaWorkspacesApi,
    private val tokenStore: BussolaTokenStore,
) {
    suspend fun list(): List<WorkspaceRead> = api.list()

    fun switchTo(workspace: WorkspaceRead) {
        tokenStore.workspaceId = workspace.id
    }

    suspend fun members(workspaceId: String): List<WorkspaceMember> = api.members(workspaceId)

    suspend fun setMemberModules(workspaceId: String, userId: String, hiddenModules: List<String>): MemberModulesUpdate =
        api.setMemberModules(workspaceId, userId, MemberModulesUpdate(hiddenModules))
}

@Singleton
class BussolaTasksRepository @Inject constructor(private val api: BussolaTasksApi) {
    suspend fun list(category: String? = null, status: String? = null): List<Task> = api.list(category, status)
    suspend fun get(id: String): Task = api.get(id)
    suspend fun create(body: TaskCreate): Task = api.create(body)
    suspend fun update(id: String, body: TaskUpdate): Task = api.update(id, body)
    suspend fun delete(id: String) = api.delete(id)

    suspend fun createSubtask(taskId: String, title: String): Subtask = api.createSubtask(taskId, SubtaskCreate(title))
    suspend fun toggleSubtask(taskId: String, subtaskId: String, isDone: Boolean): Subtask =
        api.updateSubtask(taskId, subtaskId, SubtaskUpdate(isDone = isDone))
    suspend fun renameSubtask(taskId: String, subtaskId: String, title: String): Subtask =
        api.updateSubtask(taskId, subtaskId, SubtaskUpdate(title = title))
    suspend fun deleteSubtask(taskId: String, subtaskId: String) = api.deleteSubtask(taskId, subtaskId)
}

@Singleton
class BussolaCalendarRepository @Inject constructor(private val api: BussolaCalendarApi) {
    suspend fun status(): GoogleCalendarStatus = api.status()
    suspend fun events(start: String? = null, end: String? = null): List<CalendarEventRead> = api.events(start, end)
    suspend fun createEvent(body: CalendarEventCreate): CalendarEventRead = api.createEvent(body)
    suspend fun updateEvent(id: String, calendarId: String, body: CalendarEventUpdate): CalendarEventRead =
        api.updateEvent(id, calendarId, body)
    suspend fun deleteEvent(id: String, calendarId: String) = api.deleteEvent(id, calendarId)
}

@Singleton
class BussolaCamerasRepository @Inject constructor(private val api: BussolaCamerasApi) {
    suspend fun list(): List<Camera> = api.list()
    suspend fun snapshot(location: String, cameraId: Int): ByteArray = api.snapshot(location, cameraId).bytes()
    suspend fun recordings(location: String, cameraName: String): List<CameraRecording> = api.recordings(location, cameraName)
    suspend fun search(location: String, cameraName: String, date: String?, timeFrom: String?, timeTo: String?): List<CameraRecording> =
        api.search(location, cameraName, date, timeFrom, timeTo)
    suspend fun recordingBytes(location: String, cameraName: String, filename: String): ByteArray =
        api.recording(location, cameraName, filename).bytes()
}
