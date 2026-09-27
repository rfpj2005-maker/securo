package br.com.ampararprotecao.bussola.ui.cameras

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import br.com.ampararprotecao.bussola.data.bussola.model.Camera
import br.com.ampararprotecao.bussola.data.bussola.model.CameraRecording
import br.com.ampararprotecao.bussola.data.bussola.repository.BussolaCamerasRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

val LOCATION_LABELS = mapOf(
    "matriz" to "Matriz",
    "belvedere" to "Belvedere",
    "varginha" to "Varginha",
    "centro" to "Centro",
)
fun locationLabel(location: String) = LOCATION_LABELS[location] ?: location

data class CamerasUiState(
    val loading: Boolean = true,
    val byLocation: Map<String, List<Camera>> = emptyMap(),
    val unreachableLocations: List<String> = emptyList(),
    val snapshots: Map<String, ByteArray> = emptyMap(),
    val error: String? = null,
) {
    companion object {
        fun tileKey(location: String, cameraId: Int) = "$location-$cameraId"
    }
}

@HiltViewModel
class CamerasViewModel @Inject constructor(
    private val repository: BussolaCamerasRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CamerasUiState())
    val state: StateFlow<CamerasUiState> = _state.asStateFlow()

    private var polling = false

    init { load() }

    fun load() {
        viewModelScope.launch {
            runCatching { repository.list() }
                .onSuccess { list -> applyList(list) }
                .onFailure { _state.value = _state.value.copy(loading = false, error = it.message) }
        }
        if (!polling) {
            polling = true
            startPolling()
        }
    }

    private fun applyList(list: List<Camera>) {
        val real = list.filter { it.error == null }
        val unreachable = list.filter { it.error != null }.map { it.location }
        _state.value = _state.value.copy(
            loading = false,
            byLocation = real.groupBy { it.location },
            unreachableLocations = unreachable,
        )
    }

    private fun startPolling() {
        // One shared loop: refreshes the camera/status list every 30s and,
        // on every tick, also refreshes a thumbnail for each online camera
        // — mirrors the web tile's independent 10s polling closely enough
        // without spawning one coroutine per camera.
        viewModelScope.launch {
            var tick = 0
            while (true) {
                delay(10_000)
                tick++
                if (tick % 3 == 0) {
                    runCatching { repository.list() }.onSuccess { applyList(it) }
                }
                val cameras = _state.value.byLocation.values.flatten().filter { it.online && it.id != null }
                val snapshots = _state.value.snapshots.toMutableMap()
                for (cam in cameras) {
                    val id = cam.id ?: continue
                    runCatching { repository.snapshot(cam.location, id) }
                        .onSuccess { snapshots[CamerasUiState.tileKey(cam.location, id)] = it }
                }
                _state.value = _state.value.copy(snapshots = snapshots)
            }
        }
    }
}

data class CameraDetailUiState(
    val camera: Camera? = null,
    val snapshot: ByteArray? = null,
    val recordings: List<CameraRecording> = emptyList(),
    val recordingsLoading: Boolean = true,
    val playingFile: String? = null,
    val playingUrlBytes: ByteArray? = null,
    val playingLoading: Boolean = false,
)

@HiltViewModel
class CameraDetailViewModel @Inject constructor(
    private val repository: BussolaCamerasRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CameraDetailUiState())
    val state: StateFlow<CameraDetailUiState> = _state.asStateFlow()

    private var location: String = ""
    private var cameraId: Int = 0
    private var cameraName: String = ""
    private var pollingJob: kotlinx.coroutines.Job? = null

    fun start(location: String, cameraId: Int, cameraName: String) {
        this.location = location
        this.cameraId = cameraId
        this.cameraName = cameraName
        _state.value = CameraDetailUiState(camera = Camera(location = location, id = cameraId, name = cameraName, online = true))
        loadRecordings()
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (true) {
                runCatching { repository.snapshot(location, cameraId) }
                    .onSuccess { _state.value = _state.value.copy(snapshot = it) }
                delay(3_000)
            }
        }
    }

    private fun loadRecordings() {
        if (cameraName.isBlank()) return
        viewModelScope.launch {
            _state.value = _state.value.copy(recordingsLoading = true)
            runCatching { repository.recordings(location, cameraName) }
                .onSuccess { _state.value = _state.value.copy(recordings = it, recordingsLoading = false) }
                .onFailure { _state.value = _state.value.copy(recordingsLoading = false) }
        }
    }

    fun openRecording(rec: CameraRecording) {
        viewModelScope.launch {
            _state.value = _state.value.copy(playingFile = rec.filename, playingLoading = true, playingUrlBytes = null)
            runCatching { repository.recordingBytes(location, cameraName, rec.filename) }
                .onSuccess { _state.value = _state.value.copy(playingUrlBytes = it, playingLoading = false) }
                .onFailure { _state.value = _state.value.copy(playingLoading = false) }
        }
    }

    fun closeRecording() {
        _state.value = _state.value.copy(playingFile = null, playingUrlBytes = null, playingLoading = false)
    }

    override fun onCleared() {
        pollingJob?.cancel()
        super.onCleared()
    }
}
