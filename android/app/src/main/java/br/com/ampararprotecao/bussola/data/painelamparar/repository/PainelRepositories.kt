package br.com.ampararprotecao.bussola.data.painelamparar.repository

import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelAuthApi
import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelBoletosAReceberApi
import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelCarneApi
import br.com.ampararprotecao.bussola.data.painelamparar.api.PainelNegativadosApi
import br.com.ampararprotecao.bussola.data.painelamparar.model.BoletosAReceberResult
import br.com.ampararprotecao.bussola.data.painelamparar.model.BoletosAReceberStatus
import br.com.ampararprotecao.bussola.data.painelamparar.model.CarneItem
import br.com.ampararprotecao.bussola.data.painelamparar.model.CarneStatus
import br.com.ampararprotecao.bussola.data.painelamparar.model.NegativadoItem
import br.com.ampararprotecao.bussola.data.painelamparar.model.NegativadosStatus
import br.com.ampararprotecao.bussola.data.painelamparar.model.PainelConfig
import javax.inject.Inject
import javax.inject.Singleton

/** SSO (2026-09-16): no separate login — [config] doubles as the "is my
 * Bússola account linked to a Painel Amparar identity" probe (200 vs
 * 403), called once after Bússola login to decide whether to show the
 * Painel Amparar-backed menu items at all. */
@Singleton
class PainelAuthRepository @Inject constructor(private val api: PainelAuthApi) {
    suspend fun config(): PainelConfig = api.config()
}

@Singleton
class PainelCarneRepository @Inject constructor(private val api: PainelCarneApi) {
    suspend fun list(): List<CarneItem> = api.list()
    suspend fun status(): CarneStatus = api.status()
    suspend fun verificarAgora() = api.verificarAgora()
}

@Singleton
class PainelNegativadosRepository @Inject constructor(private val api: PainelNegativadosApi) {
    suspend fun list(): List<NegativadoItem> = api.list()
    suspend fun status(): NegativadosStatus = api.status()
}

@Singleton
class PainelBoletosAReceberRepository @Inject constructor(private val api: PainelBoletosAReceberApi) {
    suspend fun result(): BoletosAReceberResult = api.result()
    suspend fun status(): BoletosAReceberStatus = api.status()
    suspend fun verificarAgora() = api.verificarAgora()
}
