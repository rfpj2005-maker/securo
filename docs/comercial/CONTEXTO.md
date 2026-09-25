# Projeto Comercial Amparar — contexto levantado

Levantado em 25/09/2026 a partir do vault do Obsidian (backup no Google Drive),
das pastas `Amparar Proteção Veicular/Claude` e `monitoramento` no Drive, e deste
repositório. **Nenhum segredo neste arquivo** — só onde cada credencial está.

## Fluxo comercial atual (relatado pelo usuário)

1. Colaborador recebe/prospecta leads e registra no CRM próprio
   (`https://crm-amparar.pages.dev/`, Cloudflare Pages).
2. Contato por **WhatsAtende** ou ligação pelo **PABX Nuvem JTi**.
3. Agenda visita com o futuro associado.
4. Faz a apresentação (`Apresentação de vendas (2).pptx`, 108 MB, Drive
   `Amparar Proteção Veicular/`, id `1J9hjAEdGhQ0Dt7GZgJUGIhsZzG3ZdzWh`).
5. Fecha a venda montando a cotação no **app do Siprov**.

Objetivo: fazer todo o fluxo num lugar só e **cadastrar associado + veículo
direto no Siprov** ao fechar.

## Onde as coisas rodam hoje

| Sistema | Onde | Observação |
|---|---|---|
| Bússola (ex-Securo) | Docker no host Tailscale `desktop-s200k6m` (`https://desktop-s200k6m.tail50b52d.ts.net`, PWA) | Fork privado `rfpj2005-maker/securo`. Código Siprov/Amparar **nunca** vai pro upstream público. `.env` só por cópia manual; `SECRET_KEY` igual entre máquinas. |
| Painel Amparar (Cobrança) | Dentro do Bússola | Fila de responsável (Naiely / Ana Gavião / Andressa), status "Atendeu", registro de contato por ligação e WhatsApp. **Bom modelo pra reaproveitar no pipeline comercial.** |
| Relatórios Siprov diários | Script `siprov-report.py` no vault (tarefa ~20h) | CSVs em `Outputs/Siprov/` (carteira, leads, vendedores, planos…). |
| Monitoramento de contatos | Drive `Amparar Proteção Veicular/Claude/monitoramento/` | `fetch.js` (PABX), `fetch-whatsapp.js`, `qualidade.js`, `transcrever.js`, `dashboard.html`. |
| Site institucional | Hostinger, preview em `ampararprotecao.com.br/novo/` | Gera lead pro consultor; WhatsApp `wa.me/5531971762140` (oculto, rastreia origem do site). |

## Siprov (Rumo Tecnologia)

- Base: `https://acesso.siprov.com.br/siprov-api`. Auth: `POST /ext/autenticacao`
  com Basic (email:senha) → `authorizationToken` (Bearer, 12h; auth dá 429 fácil).
- Credenciais: `SIPROV_API_EMAIL` / `SIPROV_API_PASSWORD` no `.env` do Bússola;
  no vault em `~/.claude/siprov-credentials.json`. Conta Amparar **#1119**,
  fornecedor da API "Claude Integration" = `codPessoa` **3047816**.
- **Endpoints de leitura já usados:**
  - `/ext/associado` (paginado, `nome`/`cpf`/`placa`)
  - `/ext/financeiro/titulo`, `/ext/financeiro/titulo/boleto`
  - `/ext/relatorio/adesao` (POST gera, GET busca; layout 4008 = cancelados)
  - `/ext/evento`, `/ext/vistoria`
  - **`/ext/crm/lead?pagina=N`** ← o Siprov **já tem um CRM de leads**
    (campos vistos: `id`, `nome`, `cpfCnpj`)
  - Referência: `/ext/administracao/vendedor`, `/ext/administracao/loja`,
    `/ext/beneficio/tipoVeiculo`, `/ext/beneficio/situacaoBeneficio`,
    `/ext/financeiro/formaPagamento`, `/ext/administracao/fornecedor/3047816`
    (planos contratados com valor).
- **Escrita (cadastro/cotação): nada confirmado ainda.** Tudo que existe hoje é
  só leitura. Pistas:
  - No painel web existe `Ferramentas → Complementos → API` (`configApi.jsf`),
    que ainda não foi explorado.
  - Situações de benefício "Em Preenchimento" e "Homologação App" têm "App
    Externo" habilitado. Sugere que o app/CRM do Siprov cria o benefício em
    preenchimento e depois homologa.
  - A "ferramenta de CRM com link individual por colaborador" apresentada à
    diretoria provavelmente é o próprio módulo CRM/cotação do Siprov. **Confirmar com a
    Rumo** se os endpoints de lead/cotação/adesão aceitam POST.
- `/ext/negociacao` foi descontinuado → `/ext/administracao/fornecedor/{codPessoa}`.
  `/ext/integracao/univers` é de outro integrador (sem acesso).

### Tabela de planos (de `planos-contratados.csv`)

Mensalidade varia por faixa (provavelmente faixa de valor FIPE — **faixas a
confirmar**):

- Bronze – Nacional Particular: 102,65 · 129,18 · 170,86 · 201,75 · 237,89 · 340,82 · 368,15 · 401,01
- Bronze – Importados: 119,15 · 145,68 · 187,36 · 218,25 · 254,39 · 357,32 · 384,65 · 417,51 · 458,10
- Prata – Importados: 143,13 · 169,66 · 211,34 · 242,23 · … · 441,49 (e 1.088,80)
- Prata – Nacional Trabalho: 879,42 · 966,52 · 1.014,62 · 1.062,85
- Moto Particular: 102,55 → 512,35 (14 faixas)
- Bronze/Prata – Caminhões: 272,05 → 1.632,40
- Ouro – Importados: 205,63
- Opcionais: Vidros 19,90 / 29,90 · Terceiros R$45 mil 19,90 · R$50 mil 21,90 ·
  R$60 mil / R$100 mil 29,90 · Assist. 24h 300 km 19,90 · 400 km 29,90 ·
  Para-brisa caminhão 45,00 · Carro reserva 7/15 dias · Rastreador

Regulamento: vidros, carro reserva e terceiros são **opcionais**; incêndio só
decorrente de colisão.

### Equipe comercial (vendedores no Siprov)

Consultores ativos por loja (`codLoja`): Matriz 4995 (Andressa, Emanuelly, Livia,
Lorena, Maria Eduarda Suvalsky, Naiely, Nicolas, Samara), 5674 (Bianca),
5675 (Melissa, Vivian), 5676 (Kennia), 5677 Pequi (Luciano, Tamires).
Representantes: Raimundo, William, Luiz Henrique. Dados completos em
`Outputs/Siprov/_referencia/vendedores.csv`.

## PABX — Nuvem JTi (BJR Soluções em Nuvem)

- API: `https://plataforma.nuvemjti.com.br/pabx/api`, docs em `.../pabx/api_doc.php`.
- Auth: headers `usuario` + `token` (usuário `api-amparar`). Credencial em
  `monitoramento/config/nuvemjti.json` no Drive.
- Endpoints usados: `/listar_historico_chamada` (CDR: data, origem, destino,
  duração, status, fila; paginado por `pos_registro_inicial`), `/listar_ramais`
  (ramal `amparar-XXXX` → nome do colaborador).
- **A confirmar na doc:** endpoint de click-to-call (originar ligação a partir do
  ramal do consultor) e download de gravação (`archive.js` já baixa gravações).

## WhatsAtende

- API: `https://api13.whatsatende.com.br` (painel em `app13`), Swagger em
  `https://api.app14.whatsatende.com.br/swagger/`.
- Auth: Bearer token da conexão (não é o JWT do painel). Credencial em
  `monitoramento/config/whatsatende.json` no Drive.
- Conexões: 1247 `ofc-principal`, 1283 `ofc-sjv`, 1284 `ofc-nao-usar`.
- `/api/messages/tickets/search` não filtra por data (só contactId/ticketId/status/page).
- Painel tem webhooks de **saída** (Contatos/Kanban/Tickets). Envio de mensagem
  pela API: **confirmar no Swagger**.

## O que ainda falta

1. **Siprov — escrita:** a API permite criar lead, cotação, associado,
   veículo e benefício? Abrir chamado na Rumo e explorar `configApi.jsf`. É o
   ponto que decide se o fechamento vai direto pro Siprov.
2. **Faixas FIPE** de cada plano (qual faixa corresponde a qual valor).
3. **CRM crm-amparar.pages.dev:** stack e repositório, e se vale manter ou
   migrar o pipeline pra dentro do Bússola ou do CRM do próprio Siprov.
4. **Apresentação:** exportar em PDF ou versão leve (o .pptx de 108 MB não
   deu pra ler).
5. **Rede do ambiente cloud do Claude:** liberar `acesso.siprov.com.br`,
   `plataforma.nuvemjti.com.br`, `api13.whatsatende.com.br` e
   `crm-amparar.pages.dev` pra testar de lá.
