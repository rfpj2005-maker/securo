package br.com.ampararprotecao.bussola.ui.components

import java.text.NumberFormat
import java.util.Locale

private val brl: NumberFormat = NumberFormat.getCurrencyInstance(Locale("pt", "BR"))
private val numberFmt: NumberFormat = NumberFormat.getNumberInstance(Locale("pt", "BR"))

fun formatBrl(value: Double?): String = if (value == null) "—" else brl.format(value)
fun formatNumber(value: Int?): String = if (value == null) "—" else numberFmt.format(value)
