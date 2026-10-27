# Câmeras Amparar — app para Fire TV

App Android TV só para ver as câmeras: substitui o tinyCam Monitor e o
Fully Kiosk (`wall.html`) no Fire TV. Não tem anúncio, serviço em segundo
plano nem nada além do vídeo.

- Mosaico de até 4 câmeras por tela, com troca automática a cada 10 s (⏯ liga/desliga).
- RTSP direto do MediaMTX, sem áudio e com buffer curto (atraso baixo).
- Reconecta sozinho (2 s → 30 s) e reinicia a câmera que travar.
- Abre sozinho quando o Fire TV liga. Fora da tela, solta todos os players.

## Controle remoto

| Tecla | Ação |
|---|---|
| ◀ ▶ na borda, ⏪ ⏩ | loja anterior / próxima |
| OK | câmera em tela cheia (◀ ▶ troca de câmera) |
| Voltar | sai da tela cheia (no mosaico, 2× para sair do app) |
| ⏯ | liga/desliga a troca automática de tela (fica salvo) |
| Menu (≡) → Recarregar | recarrega a lista |
| Menu (≡) | URL da lista de câmeras |

## Lista de câmeras

O app usa, nessa ordem: a URL configurada (guarda cópia para quando o
servidor cair) → a última cópia → `app/src/main/assets/cameras.json`
(embutido no APK, vazio de propósito).

```json
{
  "rotateSeconds": 10,
  "maxPerPage": 4,
  "stores": [
    { "name": "Matriz", "cameras": [
      { "name": "PVAdmin", "url": "rtsp://SERVIDOR:8554/pvadmin",
        "gridUrl": "rtsp://.../pvadmin_sub", "tcp": false }
    ]}
  ]
}
```

- `gridUrl` (opcional): substream para o mosaico; a tela cheia usa `url`.
  O Fire TV tem poucos decodificadores, então o mosaico com substream é o
  que mais deixa o app leve.
- `tcp: true`: força RTSP sobre TCP (útil fora da LAN, via Tailscale).
- `rotateSeconds`: intervalo da troca automática de tela (padrão 10 s). Liga/desliga com ⏯; depois de mexer no controle, espera 20 s antes de voltar a girar. Não gira em tela cheia.
- Cada item de `stores` é uma tela do mosaico.
- **Não coloque endereços nem senhas na lista embutida**: este repositório é
  público. A lista real fica só no servidor (URL remota).

Configurar a URL pelo adb, sem digitar no controle:

```sh
adb shell am start -n br.com.amparar.cameras/.MainActivity --es configUrl http://SERVIDOR:PORTA/cameras.json
```

## Build e instalação

O APK é gerado pelo GitHub Actions (workflow **Fire TV APK**) a cada push
em `firetv/`; baixe o artefato `cameras-amparar-apk` da execução.

De um PC na mesma rede/Tailscale do Fire TV (com Depuração ADB ligada):

```sh
./scripts/instalar.sh <ip-do-firetv> cameras-amparar-<n>.apk          # instala/atualiza
./scripts/instalar.sh <ip-do-firetv> cameras-amparar-<n>.apk --limpar # e desativa tinyCam/Fully
```

**Assinatura:** para atualizar sem desinstalar, crie um keystore uma vez e
salve nos secrets do repositório `FIRETV_KEYSTORE_B64` (base64 do `.jks`),
`FIRETV_KEYSTORE_PASSWORD`, `FIRETV_KEY_ALIAS` e `FIRETV_KEY_PASSWORD`. Sem
eles, cada build sai com chave diferente e o script desinstala antes de
instalar (perde só a URL configurada).
