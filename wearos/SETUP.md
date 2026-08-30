# Configurando do zero: Android Studio + Galaxy Watch

Guia pra quem nunca instalou um app fora da Play Store num relógio. Depois
de fazer isso uma vez, o ciclo normal é só "Run" no Android Studio.

## 1. Instalar o Android Studio

1. Baixe em https://developer.android.com/studio e instale (padrão, próximo,
   próximo).
2. Na primeira abertura, deixe o "Setup Wizard" baixar o SDK Android
   (marca sozinho as opções recomendadas).

## 2. Abrir o projeto

1. Android Studio → **Open** → selecione a pasta `wearos/` (esta pasta,
   não a raiz do `securo`).
2. Ele vai avisar que falta o Gradle Wrapper (`gradlew`) — clique em **OK**
   / **Sync Now** quando perguntar; o Android Studio gera isso sozinho na
   primeira sincronização.
3. Espere o "Gradle Sync" terminar (barra de progresso embaixo). Se pedir
   pra instalar alguma versão de SDK/build-tools, aceite.

## 3. Ativar o modo desenvolvedor no relógio

No **relógio** (não no celular):

1. Configurações → Sobre → toque 5 vezes em "Número da versão do software"
   até aparecer "Modo desenvolvedor ativado".
2. Volte pra Configurações → agora tem um menu novo "Opções do desenvolvedor".
3. Dentro dele, ative:
   - **Depuração ADB**
   - **Depurar via Wi-Fi** (mostra um IP e uma porta, tipo `192.168.1.50:5555`
     — anote isso)

O relógio precisa estar na **mesma rede Wi-Fi** que o computador com o
Android Studio.

## 4. Conectar o Android Studio ao relógio

No terminal (View → Tool Windows → Terminal, dentro do Android Studio, ou
qualquer terminal com `adb` no PATH — o Android Studio instala o `adb`
junto com o SDK, geralmente em
`%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe` no Windows):

```bash
adb connect 192.168.1.50:5555
```

(troque pelo IP:porta que apareceu no relógio). Se der certo, `adb devices`
lista o relógio como `device` (não `unauthorized` — se aparecer isso,
confirme a caixa de diálogo de permissão que aparece no *relógio*).

## 5. Rodar

No Android Studio, escolha o módulo **app** no seletor de configuração de
execução (ao lado do botão ▶️ verde) e clique em Run. O relógio aparece
como dispositivo de destino automaticamente depois do `adb connect`.

Pra instalar o mostrador (watch face), troque o seletor pro módulo
**watchface** e rode de novo — depois, no próprio relógio, segure a tela
do mostrador atual → escolha o mostrador "Securo" na lista.

## O que esperar na primeira vez

Este projeto foi escrito sem poder compilar/testar localmente (sem
ambiente Android disponível nesta sessão) — é bem provável que o primeiro
Gradle Sync ou build aponte 1-2 erros pequenos de API (nomes de classe que
mudaram de versão, um import faltando). Isso é normal pra um projeto novo
como este; me manda o erro exato que aparece (a mensagem completa do
Android Studio) que eu ajusto o código.

## Testando o pareamento

1. No relógio: abra o app Securo → tela de pareamento → toque em "Confirmar"
   → escolha digitar/ditar o código.
2. No celular ou PC, no app Securo (https://desktop-s200k6m.tail50b52d.ts.net):
   menu do usuário → **Parear relógio** → aparece um código de 6 dígitos.
3. Digite esse código no relógio. Se der certo, cai direto na tela de
   Tarefas.

Se a tela de Tarefas/Calendário ficar carregando pra sempre ou der erro,
o motivo mais provável é o relógio não conseguir alcançar
`https://desktop-s200k6m.tail50b52d.ts.net` pela rede dele (Wi-Fi de casa,
Bluetooth-relay via celular, etc.) — veja a nota sobre isso no plano
original. Testar isso é o primeiro passo antes de mexer em mais telas.
