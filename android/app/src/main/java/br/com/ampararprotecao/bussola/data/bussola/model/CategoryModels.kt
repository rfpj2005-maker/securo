package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CategoryGroup(
    val id: String,
    val name: String,
    val icon: String = "folder",
    val color: String = "#6B7280",
    val position: Int = 0,
    @SerialName("is_system") val isSystem: Boolean = false,
    val categories: List<Category> = emptyList(),
)

@Serializable
data class CategoryCreate(
    val name: String,
    val icon: String = "circle-help",
    val color: String = "#6B7280",
    @SerialName("group_id") val groupId: String? = null,
)

@Serializable
data class CategoryUpdate(
    val name: String? = null,
    val icon: String? = null,
    val color: String? = null,
    @SerialName("group_id") val groupId: String? = null,
)
