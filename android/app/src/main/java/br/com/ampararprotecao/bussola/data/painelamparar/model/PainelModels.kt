package br.com.ampararprotecao.bussola.data.painelamparar.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PainelConfig(
    @SerialName("usuario") val usuario: String,
    @SerialName("nome") val nome: String,
    @SerialName("admin") val admin: Boolean = false,
    @SerialName("features") val features: List<String> = emptyList(),
    @SerialName("carteira") val carteira: PainelCarteira? = null,
)

@Serializable
data class PainelCarteira(
    @SerialName("stats") val stats: Map<String, Int> = emptyMap(),
    @SerialName("fetchedAt") val fetchedAt: String? = null,
)

@Serializable
data class CarneItem(
    @SerialName("sequencial") val sequencial: Int,
    @SerialName("nome") val nome: String,
    @SerialName("placa") val placa: String,
    @SerialName("cpfCnpj") val cpfCnpj: String,
    @SerialName("qtdBoletosFuturos") val qtdBoletosFuturos: Int,
    @SerialName("cobertoAte") val cobertoAte: String,
    @SerialName("diasRestantes") val diasRestantes: Int,
    @SerialName("precisaRenovarEmBreve") val precisaRenovarEmBreve: Boolean,
)

@Serializable
data class CarneStatus(
    @SerialName("syncing") val syncing: Boolean = false,
    @SerialName("lastSync") val lastSync: String? = null,
    @SerialName("lastError") val lastError: String? = null,
    @SerialName("ativosVerificados") val ativosVerificados: Int = 0,
    @SerialName("pendentesCount") val pendentesCount: Int = 0,
    @SerialName("renovarEmBreveCount") val renovarEmBreveCount: Int = 0,
)

@Serializable
data class BoletoAberto(
    @SerialName("codTitulo") val codTitulo: Long,
    @SerialName("valor") val valor: Double,
    @SerialName("descricao") val descricao: String = "",
    @SerialName("dataVencimento") val dataVencimento: String? = null,
    @SerialName("diasAtraso") val diasAtraso: Int? = null,
)

@Serializable
data class NegativadoItem(
    @SerialName("id") val id: String,
    @SerialName("nome") val nome: String,
    @SerialName("placa") val placa: String,
    @SerialName("cpfCnpj") val cpfCnpj: String = "",
    @SerialName("situacaoAtual") val situacaoAtual: String,
    @SerialName("telefone") val telefone: String = "",
    @SerialName("valorMensalidade") val valorMensalidade: Double? = null,
    @SerialName("cartaEnviada") val cartaEnviada: Boolean = false,
    @SerialName("statusResultado") val statusResultado: String = "pendente",
    @SerialName("boletosAbertos") val boletosAbertos: List<BoletoAberto> = emptyList(),
    @SerialName("valorEmAberto") val valorEmAberto: Double? = null,
)

@Serializable
data class NegativadosStatus(
    @SerialName("syncing") val syncing: Boolean = false,
    @SerialName("lastSync") val lastSync: String? = null,
    @SerialName("lastError") val lastError: String? = null,
    @SerialName("lastCount") val lastCount: Int = 0,
    @SerialName("porSituacao") val porSituacao: Map<String, Int> = emptyMap(),
    @SerialName("qtdTitulosAbertos") val qtdTitulosAbertos: Int = 0,
)

@Serializable
data class FaixaBoletos(
    @SerialName("chave") val chave: String,
    @SerialName("label") val label: String,
    @SerialName("qtd") val qtd: Int,
    @SerialName("valor") val valor: Double,
)

@Serializable
data class BoletosAReceberResult(
    @SerialName("mesReferencia") val mesReferencia: String? = null,
    @SerialName("faixas") val faixas: List<FaixaBoletos> = emptyList(),
    @SerialName("totalQtd") val totalQtd: Int = 0,
    @SerialName("totalValor") val totalValor: Double = 0.0,
)

@Serializable
data class BoletosAReceberStatus(
    @SerialName("syncing") val syncing: Boolean = false,
    @SerialName("lastSync") val lastSync: String? = null,
    @SerialName("lastError") val lastError: String? = null,
    @SerialName("totalTitulosAbertos") val totalTitulosAbertos: Int = 0,
)
