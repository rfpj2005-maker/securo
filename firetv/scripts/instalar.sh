#!/usr/bin/env bash
# Instala/atualiza o app "Câmeras Amparar" no Fire TV pela rede (adb).
# Uso: ./instalar.sh <ip-do-firetv> <arquivo.apk> [--limpar]
#   --limpar  também desativa tinyCam e Fully Kiosk (só depois de conferir o app novo).
# Pré-requisito no Fire TV: Configurações > Minha Fire TV > Opções do desenvolvedor >
#   Depuração ADB = Ligada (e "Apps de origem desconhecida" para o adb).
set -euo pipefail

IP="${1:?informe o IP do Fire TV}"
APK="${2:?informe o arquivo .apk}"
PKG="br.com.amparar.cameras"

adb connect "$IP:5555"
adb -s "$IP:5555" wait-for-device

echo "Instalando $APK…"
if ! out=$(adb -s "$IP:5555" install -r "$APK" 2>&1); then
  echo "$out"
  if grep -q "INSTALL_FAILED_UPDATE_INCOMPATIBLE" <<<"$out"; then
    echo "Assinatura diferente da versão instalada: desinstalando e instalando de novo."
    adb -s "$IP:5555" uninstall "$PKG" || true
    adb -s "$IP:5555" install "$APK"
  else
    exit 1
  fi
fi

S="adb -s $IP:5555 shell"
# Abrir sozinho ao ligar a TV (Fire OS 7+ bloqueia abrir tela em 2º plano sem isso).
$S appops set "$PKG" SYSTEM_ALERT_WINDOW allow || true
# Não deixar o Fire TV dormir nem ligar descanso de tela por cima das câmeras.
$S settings put secure screensaver_enabled 0 || true
$S settings put system screen_off_timeout 2147483647 || true
$S settings put secure sleep_timeout 0 || true

if [[ "${3:-}" == "--limpar" ]]; then
  for app in com.alexvas.dvr com.alexvas.dvr.pro de.ozerov.fully; do
    if $S pm list packages | grep -q "package:$app\$"; then
      echo "Desativando $app"
      $S pm disable-user --user 0 "$app" || true
    fi
  done
fi

$S am start -n "$PKG/.MainActivity"
echo "Pronto."
