package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * `POST /api/auth/login` and `POST /api/auth/2fa/verify` both return this
 * shape: either the JWT pair, or (login only) a 2FA challenge. Backend:
 * `backend/app/api/custom_auth.py`. All DTOs in this package spell out
 * `@SerialName` explicitly rather than relying on an automatic snake_case
 * strategy — fields like `is_2fa_enabled` don't round-trip predictably
 * through a generic camelCase<->snake_case converter, and a silent null
 * from a mismatched key is a much worse failure mode than a bit of
 * verbosity here.
 */
@Serializable
data class LoginResponse(
    @SerialName("access_token") val accessToken: String? = null,
    @SerialName("token_type") val tokenType: String? = null,
    @SerialName("requires_2fa") val requiresTfa: Boolean = false,
    @SerialName("temp_token") val tempToken: String? = null,
    @SerialName("available_methods") val availableMethods: List<String> = emptyList(),
)

@Serializable
data class ForgotPasswordRequest(
    @SerialName("email") val email: String,
)

@Serializable
data class TwoFactorVerifyRequest(
    @SerialName("temp_token") val tempToken: String,
    @SerialName("code") val code: String,
)

@Serializable
data class UserPreferences(
    @SerialName("language") val language: String? = null,
    @SerialName("date_format") val dateFormat: String? = null,
    @SerialName("timezone") val timezone: String? = null,
    @SerialName("currency_display") val currencyDisplay: String? = null,
    @SerialName("default_workspace_id") val defaultWorkspaceId: String? = null,
)

@Serializable
data class UserRead(
    @SerialName("id") val id: String,
    @SerialName("email") val email: String,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("is_superuser") val isSuperuser: Boolean = false,
    @SerialName("is_verified") val isVerified: Boolean = true,
    @SerialName("is_2fa_enabled") val is2faEnabled: Boolean = false,
    @SerialName("preferences") val preferences: UserPreferences? = null,
)
