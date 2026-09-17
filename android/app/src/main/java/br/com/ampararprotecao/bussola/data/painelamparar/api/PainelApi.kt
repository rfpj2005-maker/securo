package br.com.ampararprotecao.bussola.data.painelamparar.api

import br.com.ampararprotecao.bussola.data.painelamparar.model.BoletosAReceberResult
import br.com.ampararprotecao.bussola.data.painelamparar.model.BoletosAReceberStatus
import br.com.ampararprotecao.bussola.data.painelamparar.model.CarneItem
import br.com.ampararprotecao.bussola.data.painelamparar.model.CarneStatus
import br.com.ampararprotecao.bussola.data.painelamparar.model.NegativadoItem
import br.com.ampararprotecao.bussola.data.painelamparar.model.NegativadosStatus
import br.com.ampararprotecao.bussola.data.painelamparar.model.PainelConfig
import retrofit2.http.GET
import retrofit2.http.POST

interface PainelAuthApi {
    // SSO (2026-09-16): no login endpoint here anymore — Painel Amparar
    // verifies the same Bússola Bearer token. This call doubles as the
    // "is my Bússola account actually linked to a Painel Amparar
    // identity" check: 200 = yes, 403 = no (see bussola-auth.js).
    @GET("config")
    suspend fun config(): PainelConfig
}

interface PainelCarneApi {
    @GET("carne")
    suspend fun list(): List<CarneItem>

    @GET("carne/status")
    suspend fun status(): CarneStatus

    @POST("carne/verificar-agora")
    suspend fun verificarAgora()
}

interface PainelNegativadosApi {
    @GET("negativados")
    suspend fun list(): List<NegativadoItem>

    @GET("negativados/status")
    suspend fun status(): NegativadosStatus
}

interface PainelBoletosAReceberApi {
    @GET("boletos-a-receber")
    suspend fun result(): BoletosAReceberResult

    @GET("boletos-a-receber/status")
    suspend fun status(): BoletosAReceberStatus

    @POST("boletos-a-receber/verificar-agora")
    suspend fun verificarAgora()
}
