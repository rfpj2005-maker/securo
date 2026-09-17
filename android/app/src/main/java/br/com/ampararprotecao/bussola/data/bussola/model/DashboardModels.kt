package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Matches `backend/app/schemas/dashboard.py`'s `DashboardSummary` exactly —
 * `monthly_income`/`monthly_expenses` are plain floats (already in
 * whatever currency the account itself is), NOT a currency->amount map
 * like `total_balance` is. Mixing those up crashed the whole decode on
 * first real-device run (kotlinx.serialization has no partial-failure
 * mode: one field's shape mismatch fails the entire object). The
 * `*_primary` fields are the backend's own currency-consolidated numbers
 * — use those for display instead of trying to look values up out of the
 * `total_balance` map by `primary_currency`. */
@Serializable
data class DashboardSummary(
    @SerialName("total_balance") val totalBalance: Map<String, Double> = emptyMap(),
    @SerialName("total_balance_primary") val totalBalancePrimary: Double = 0.0,
    @SerialName("monthly_income") val monthlyIncome: Double = 0.0,
    @SerialName("monthly_expenses") val monthlyExpenses: Double = 0.0,
    @SerialName("monthly_income_primary") val monthlyIncomePrimary: Double = 0.0,
    @SerialName("monthly_expenses_primary") val monthlyExpensesPrimary: Double = 0.0,
    @SerialName("pending_categorization") val pendingCategorization: Int = 0,
    @SerialName("primary_currency") val primaryCurrency: String = "BRL",
)

@Serializable
data class SpendingByCategory(
    @SerialName("category_id") val categoryId: String,
    @SerialName("category_name") val categoryName: String,
    @SerialName("category_icon") val categoryIcon: String? = null,
    @SerialName("category_color") val categoryColor: String? = null,
    @SerialName("total") val total: Double,
    @SerialName("percentage") val percentage: Double = 0.0,
)
