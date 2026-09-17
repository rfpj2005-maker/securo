package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class WorkspaceRead(
    @SerialName("id") val id: String,
    @SerialName("name") val name: String,
    @SerialName("kind") val kind: String,
    @SerialName("is_archived") val isArchived: Boolean = false,
    @SerialName("default_currency") val defaultCurrency: String = "BRL",
    @SerialName("icon") val icon: String? = null,
    @SerialName("color") val color: String? = null,
    @SerialName("role") val role: String? = null,
    @SerialName("enabled_modules") val enabledModules: List<String> = emptyList(),
    @SerialName("enabled_features") val enabledFeatures: List<String> = emptyList(),
) {
    fun hasFeature(id: String) = enabledFeatures.contains(id)
}

@Serializable
data class WorkspaceMember(
    @SerialName("user_id") val userId: String,
    @SerialName("display_name") val displayName: String,
    @SerialName("role") val role: String,
    @SerialName("hidden_modules") val hiddenModules: List<String> = emptyList(),
)

@Serializable
data class MemberModulesUpdate(
    @SerialName("hidden_modules") val hiddenModules: List<String>,
)
