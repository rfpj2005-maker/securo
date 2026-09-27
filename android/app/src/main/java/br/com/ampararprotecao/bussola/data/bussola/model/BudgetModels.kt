package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class BudgetVsActual(
    @SerialName("category_id") val categoryId: String,
    @SerialName("category_name") val categoryName: String,
    @SerialName("category_icon") val categoryIcon: String? = null,
    @SerialName("category_color") val categoryColor: String? = null,
    @SerialName("group_id") val groupId: String? = null,
    @SerialName("group_name") val groupName: String? = null,
    @SerialName("budget_amount") val budgetAmount: String? = null,
    @SerialName("actual_amount") val actualAmount: String = "0",
    @SerialName("percentage_used") val percentageUsed: Double? = null,
    @SerialName("is_recurring") val isRecurring: Boolean = false,
)

@Serializable
data class Budget(
    val id: String,
    @SerialName("category_id") val categoryId: String,
    val amount: String,
    val month: String,
    @SerialName("is_recurring") val isRecurring: Boolean = false,
)

@Serializable
data class BudgetCreate(
    @SerialName("category_id") val categoryId: String,
    val amount: String,
    val month: String,
    @SerialName("is_recurring") val isRecurring: Boolean = false,
)

@Serializable
data class BudgetUpdate(
    val amount: String? = null,
)
