package br.com.ampararprotecao.bussola.data.bussola.api

import br.com.ampararprotecao.bussola.data.bussola.model.Account
import br.com.ampararprotecao.bussola.data.bussola.model.Category
import br.com.ampararprotecao.bussola.data.bussola.model.DashboardSummary
import br.com.ampararprotecao.bussola.data.bussola.model.LoginResponse
import br.com.ampararprotecao.bussola.data.bussola.model.MemberModulesUpdate
import br.com.ampararprotecao.bussola.data.bussola.model.PaginatedTransactions
import br.com.ampararprotecao.bussola.data.bussola.model.SpendingByCategory
import br.com.ampararprotecao.bussola.data.bussola.model.Transaction
import br.com.ampararprotecao.bussola.data.bussola.model.TransactionEditPayload
import br.com.ampararprotecao.bussola.data.bussola.model.TwoFactorVerifyRequest
import br.com.ampararprotecao.bussola.data.bussola.model.UserRead
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceMember
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceRead
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
}

interface BussolaAccountsApi {
    @GET("accounts")
    suspend fun list(@Query("include_closed") includeClosed: Boolean = false): List<Account>
}
