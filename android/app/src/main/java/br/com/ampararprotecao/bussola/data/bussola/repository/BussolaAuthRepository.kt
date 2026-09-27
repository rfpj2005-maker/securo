package br.com.ampararprotecao.bussola.data.bussola.repository

import br.com.ampararprotecao.bussola.data.BussolaTokenStore
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaAuthApi
import br.com.ampararprotecao.bussola.data.bussola.api.BussolaWorkspacesApi
import br.com.ampararprotecao.bussola.data.bussola.model.LoginResponse
import br.com.ampararprotecao.bussola.data.bussola.model.UserRead
import br.com.ampararprotecao.bussola.data.bussola.model.WorkspaceRead
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BussolaAuthRepository @Inject constructor(
    private val authApi: BussolaAuthApi,
    private val workspacesApi: BussolaWorkspacesApi,
    private val tokenStore: BussolaTokenStore,
) {
    suspend fun login(username: String, password: String): LoginResponse = authApi.login(username, password)

    suspend fun verifyTwoFactor(
        tempToken: String,
        code: String,
    ): LoginResponse = authApi.verifyTwoFactor(
        br.com.ampararprotecao.bussola.data.bussola.model.TwoFactorVerifyRequest(tempToken, code),
    )

    /** Stores the JWT, fetches the user + workspace list, resolves the
     * default workspace with the SAME rule as the backend/web (preferences'
     * default_workspace_id if it's a workspace the user still belongs to,
     * else the first one), and stamps it into the token store. */
    suspend fun completeLogin(loginResponse: LoginResponse): WorkspaceRead {
        tokenStore.accessToken = loginResponse.accessToken
        val user: UserRead = authApi.me()
        tokenStore.isSuperuser = user.isSuperuser
        val workspaces = workspacesApi.list()
        val preferred = user.preferences?.defaultWorkspaceId
        val resolved = workspaces.firstOrNull { it.id == preferred } ?: workspaces.first()
        tokenStore.workspaceId = resolved.id
        return resolved
    }

    suspend fun forgotPassword(email: String) = authApi.forgotPassword(
        br.com.ampararprotecao.bussola.data.bussola.model.ForgotPasswordRequest(email),
    )

    fun logout() = tokenStore.clear()
}
