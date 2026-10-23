# Câmeras Amparar — app para Fire TV

App Android TV só para ver as câmeras: substitui o tinyCam Monitor e o
Fully Kiosk (`wall.html`) no Fire TV. Não tem anúncio, serviço em segundo
plano nem nada além do vídeo.

- Mosaico por loja (até `maxPerPage` câmeras por tela, padrão 4).
- RTSP direto do MediaMTX, sem áudio e com buffer curto (atraso baixo).
- Reconecta sozinho (2 s → 30 s) e reinicia a câmera que travar.
- Abre sozinho quando o Fire TV liga. Fora da tela, solta todos os players.

## Controle remoto

| Tecla | Ação |
|---|---|
| ◀ ▶ na borda, ⏪ ⏩ | loja anterior / próxima |
| OK | câmera em tela cheia (◀ ▶ troca de câmera) |
| Voltar | sai da tela cheia (no mosaico, 2× para sair do app) |
| ⏯ | recarrega a lista |
| Menu (≡) | URL da lista de câmeras |

## Lista de câmeras

O app usa, nessa ordem: a URL configurada (guarda cópia para quando o
servidor cair) → a última cópia → `app/src/main/assets/cameras.json`
(embutido no APK).

```json
{
  "rotateSeconds": 0,
  "maxPerPage": 4,
  "stores": [
    { "name": "Matriz", "cameras": [
      { "name": "PVAdmin", "url": "rtsp://192.168.18.107:8554/pvadmin",
        "gridUrl": "rtsp://.../pvadmin_sub", "tcp": false }
    ]}
  ]
}
```

- `gridUrl` (opcional): substream para o mosaico; a tela cheia usa `url`.
  O Fire TV tem poucos decodificadores, então o mosaico com substream é o
  que mais deixa o app leve.
- `tcp: true`: força RTSP sobre TCP (útil fora da LAN, via Tailscale).
- `rotateSeconds` > 0: troca de loja sozinho depois de 1 min sem mexer.
- Não coloque senha na lista embutida (vai para o repositório). Se o
  MediaMTX pedir login, use a URL remota.

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
