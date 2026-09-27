package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class RecurringTransaction(
    val id: String,
    @SerialName("account_id") val accountId: String? = null,
    @SerialName("category_id") val categoryId: String? = null,
    val description: String,
    val amount: String,
    val type: String,
    val frequency: String,
    @SerialName("day_of_month") val dayOfMonth: Int? = null,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("next_occurrence") val nextOccurrence: String? = null,
)

@Serializable
data class RecurringTransactionCreate(
    val description: String,
    val amount: String,
    val type: String,
    val frequency: String,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String? = null,
    @SerialName("account_id") val accountId: String,
    @SerialName("category_id") val categoryId: String? = null,
)

@Serializable
data class RecurringTransactionUpdate(
    val description: String? = null,
    val amount: String? = null,
    val type: String? = null,
    val frequency: String? = null,
    @SerialName("start_date") val startDate: String? = null,
    @SerialName("end_date") val endDate: String? = null,
    @SerialName("account_id") val accountId: String? = null,
    @SerialName("category_id") val categoryId: String? = null,
    @SerialName("is_active") val isActive: Boolean? = null,
)

val RECURRING_FREQUENCIES = listOf("weekly", "monthly", "quarterly", "yearly")
val RECURRING_FREQUENCY_LABELS = mapOf(
    "weekly" to "Semanal", "monthly" to "Mensal", "quarterly" to "Trimestral", "yearly" to "Anual",
)
