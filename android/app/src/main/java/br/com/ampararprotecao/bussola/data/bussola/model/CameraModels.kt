package br.com.ampararprotecao.bussola.data.bussola.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** `/api/cameras` returns a mixed list: entries with `error` mean that
 * location's recording server couldn't be reached at all — everything
 * else is nullable so either shape parses into the same class instead of
 * needing a sealed/polymorphic decoder for two rarely-both-populated
 * variants. */
@Serializable
data class Camera(
    val location: String,
    val id: Int? = null,
    val name: String? = null,
    @SerialName("display_name") val displayName: String? = null,
    val directory: String? = null,
    val online: Boolean = false,
    val connected: Boolean = false,
    val connecting: Boolean = false,
    val width: Int = 0,
    val height: Int = 0,
    val hasRecordings: Boolean = false,
    val error: String? = null,
) {
    val label: String get() = displayName ?: name ?: location
}

@Serializable
data class CameraRecording(
    val filename: String,
    val size: Long,
    val modified: String,
)
