package br.com.ampararprotecao.bussola.ui.cameras

import android.graphics.BitmapFactory
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayCircle
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import br.com.ampararprotecao.bussola.data.bussola.model.CameraRecording
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.regex.Pattern

@Composable
fun CameraDetailScreen(
    modifier: Modifier = Modifier,
    location: String,
    cameraId: Int,
    cameraName: String,
    viewModel: CameraDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(location, cameraId, cameraName) { viewModel.start(location, cameraId, cameraName) }

    Column(modifier.fillMaxSize()) {
        val bitmap = remember(state.snapshot) {
            state.snapshot?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }
        }
        Box(
            Modifier
                .fillMaxWidth()
                .height(220.dp)
                .background(MaterialTheme.colorScheme.surfaceVariant),
        ) {
            if (bitmap != null) {
                Image(bitmap.asImageBitmap(), contentDescription = state.camera?.label, modifier = Modifier.fillMaxSize())
            } else if (state.camera?.online == false) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.WifiOff, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            }
        }

        Text(
            "Gravações",
            style = MaterialTheme.typography.titleSmall,
            modifier = Modifier.padding(16.dp),
        )

        if (state.recordingsLoading) {
            Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        } else if (state.recordings.isEmpty()) {
            Text(
                "Nenhuma gravação encontrada",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        } else {
            LazyColumn(Modifier.fillMaxSize()) {
                items(state.recordings, key = { it.filename }) { rec ->
                    RecordingRow(rec, onClick = { viewModel.openRecording(rec) })
                }
            }
        }
    }

    if (state.playingFile != null) {
        RecordingPlayerDialog(
            loading = state.playingLoading,
            bytes = state.playingUrlBytes,
            onClose = { viewModel.closeRecording() },
        )
    }
}

@Composable
private fun RecordingRow(rec: CameraRecording, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Icon(Icons.Filled.PlayCircle, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(formatRecordingTime(rec), style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        Text(
            "${"%.1f".format(rec.size / (1024.0 * 1024.0))} MB",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun RecordingPlayerDialog(loading: Boolean, bytes: ByteArray?, onClose: () -> Unit) {
    val context = LocalContext.current
    androidx.compose.ui.window.Dialog(onDismissRequest = onClose) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(260.dp)
                .background(androidx.compose.ui.graphics.Color.Black),
        ) {
            if (loading || bytes == null) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            } else {
                val uri = remember(bytes) {
                    val file = File.createTempFile("rec_", ".mp4", context.cacheDir)
                    file.writeBytes(bytes)
                    Uri.fromFile(file)
                }
                val player = remember(uri) {
                    ExoPlayer.Builder(context).build().apply {
                        setMediaItem(MediaItem.fromUri(uri))
                        prepare()
                        playWhenReady = true
                    }
                }
                DisposableEffect(player) { onDispose { player.release() } }
                AndroidView(
                    factory = { PlayerView(it).apply { this.player = player } },
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}

private val RECORDING_FILENAME_TIMESTAMP = Pattern.compile("_(\\d{4}-\\d{2}-\\d{2})_(\\d{2})-(\\d{2})-(\\d{2})_")

private fun formatRecordingTime(rec: CameraRecording): String {
    val matcher = RECORDING_FILENAME_TIMESTAMP.matcher(rec.filename)
    return if (matcher.find()) {
        "${matcher.group(1)} ${matcher.group(2)}:${matcher.group(3)}:${matcher.group(4)}"
    } else {
        runCatching {
            val fmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
            fmt.format(fmt.parse(rec.modified.take(19))!!)
        }.getOrDefault(rec.modified)
    }
}
