package br.com.ampararprotecao.bussola.data.bussola.repository

import br.com.ampararprotecao.bussola.data.BussolaTokenStore
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaAccountsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaCategoriesApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaDashboardApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaTransactionsApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaWorkspacesApi
import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.DashboardSummary
import br.com.ampararprotecao.bussola.data.bussola.model.MemberModulesUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.PaginatedTransactions
import br.com.ampararprotecao.bussola.data.bussola.model.SpendingByCategory
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
