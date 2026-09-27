package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Category(
    @SerialName("id") val id: String,
    @SerialName("group_id") val groupId: String? = null,
    @SerialName("name") val name: String,
    @SerialName("icon") val icon: String? = null,
    @SerialName("color") val color: String? = null,
    @SerialName("is_system") val isSystem: Boolean = false,
    @SerialName("treat_as_transfer") val treatAsTransfer: Boolean = false,
    @SerialName("is_ignored") val isIgnored: Boolean = false,
)

/** `balance` (from AccountBase) is the manually-set starting balance used
 * by the edit form on web — NOT what's shown as "the balance" on the
 * accounts list there. `current_balance` is that (accounts.tsx:486); this
 * screen is read-only, so it's the only one of the two we need. */
@Serializable
data class Account(
    @SerialName("id") val id: String,
    @SerialName("name") val name: String,
    @SerialName("display_name") val displayName: String? = null,
    @SerialName("type") val type: String,
    @SerialName("current_balance") val currentBalance: Double = 0.0,
    @SerialName("currency") val currency: String = "BRL",
    @SerialName("is_closed") val isClosed: Boolean = false,
)

@Serializable
data class Transaction(
    @SerialName("id") val id: String,
    @SerialName("account_id") val accountId: String? = null,
    @SerialName("category_id") val categoryId: String? = null,
    @SerialName("category") val category: Category? = null,
    @SerialName("description") val description: String,
    @SerialName("amount") val amount: Double,
    @SerialName("currency") val currency: String = "BRL",
    @SerialName("date") val date: String,
    @SerialName("type") val type: String,
    @SerialName("status") val status: String = "posted",
    @SerialName("payee_name") val payeeName: String? = null,
    @SerialName("notes") val notes: String? = null,
    @SerialName("transfer_pair_id") val transferPairId: String? = null,
)

@Serializable
data class PaginatedTransactions(
    @SerialName("items") val items: List<Transaction>,
    @SerialName("total") val total: Int,
    @SerialName("page") val page: Int,
    @SerialName("limit") val limit: Int,
)

/** Body for both `POST /api/transactions` (create) and `PATCH
 * /api/transactions/{id}` (update) — Fase 1's basic field set only, see
 * the plan's "fora do escopo" list for what's deliberately left out. */
@Serializable
data class TransactionEditPayload(
    @SerialName("description") val description: String? = null,
    @SerialName("amount") val amount: Double? = null,
    @SerialName("currency") val currency: String? = null,
    @SerialName("date") val date: String? = null,
    @SerialName("type") val type: String? = null,
    @SerialName("account_id") val accountId: String? = null,
    @SerialName("category_id") val categoryId: String? = null,
    @SerialName("notes") val notes: String? = null,
)
