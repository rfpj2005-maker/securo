package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Goal(
    val id: String,
    val name: String,
    @SerialName("target_amount") val targetAmount: String,
    @SerialName("current_amount") val currentAmount: String,
    val currency: String = "BRL",
    @SerialName("target_date") val targetDate: String? = null,
    @SerialName("tracking_type") val trackingType: String = "manual",
    val status: String = "active",
    val color: String? = null,
)

@Serializable
data class GoalCreate(
    val name: String,
    @SerialName("target_amount") val targetAmount: String,
    @SerialName("current_amount") val currentAmount: String = "0",
    @SerialName("target_date") val targetDate: String? = null,
    @SerialName("tracking_type") val trackingType: String = "manual",
)

@Serializable
data class GoalUpdate(
    val name: String? = null,
    @SerialName("target_amount") val targetAmount: String? = null,
    @SerialName("current_amount") val currentAmount: String? = null,
    @SerialName("target_date") val targetDate: String? = null,
    val status: String? = null,
)
