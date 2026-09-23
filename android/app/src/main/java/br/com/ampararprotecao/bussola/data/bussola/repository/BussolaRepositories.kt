package br.com.ampararprotecao.bussola.data.bussola.repository

import br.com.ampararprotecao.bussola.data.BussolaTokenStore
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaAccountsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCalendarApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCategoriesApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaDashboardApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaTasksApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaTransactionsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaWorkspacesApi
import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventCreate
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventRead
import br.com.ampararprotecao.bussola.data.bussola.model.CalendarEventUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.DashboardSummary
import br.com.ampararprotecao.bussola.data.bussola.model.GoogleCalendarStatus
import br.com.ampararprotecao.bussola.data.bussola.model.MemberModulesUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.PaginatedTransactions
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
