# Estado atual do trabalho (para abrir uma sessão limpa)

Atualizado em 2026-10-29 (sessão na nuvem: ver a seção logo abaixo). Os prompts de origem citados estão em
`C:\Users\User\Desktop\Claude outputs\` (os mais antigos já não estão no disco; o que eles pediram está nos cartões
de `notas/PENDENCIAS_PARA_O_PEDRO.md` e nas notas de decisão).

## Sessão na nuvem (desde 2026-10-28): LEIA ESTA SEÇÃO PRIMEIRO

O Pedro passou o projeto para uma sessão na nuvem (Linux, o mesmo sistema do CI). Só vale o que está no GitHub. O plano da v2 e as
respostas do Pedro estão em `notas/design/v2/` (`PLANO-v2-0.md`, `PROMPT-MESTRE-fila-do-projeto.md`,
`PROMPT-respostas-v2-0-e-pendencias.md`, `LISTA-O-QUE-FALTA.md`); onde este arquivo cita `C:/Users/User/Desktop/Claude outputs/`,
use a cópia daqui. Relatórios ao Pedro em linguagem simples (ele lê no celular).

**Ambiente da nuvem:** Python 3.12 num venv (`python3.12 -m venv`, `pip install -r requirements-dev.txt`); o Chromium do Playwright
já vem instalado (`/opt/pw-browsers`, não rodar `playwright install`). Não há `data/interim/`, demos `.dem` nem `.rar`: tarefa que
precise delas para e avisa o Pedro. A `compara_capturas` pede `channel="chrome"`, que não existe aqui: a prova da v2-5b usou as
funções dela com o Chromium (as referências de antes eram do Chrome no Windows). O `github.io` é bloqueado pelo proxy da sessão:
o deploy se confere pela API (`deployments?environment=github-pages`). A sessão não consegue apagar branch no GitHub (o proxy
derruba o pedido): pedir ao Pedro.

**Testes pulados aqui (142 a 143 de ~1.600; lista de 2026-10-29, `pytest -rs`):** a suíte da nuvem NÃO roda o que depende do dado
local. **Regra do Pedro (2026-10-29): tarefa que mexe em MÉTRICA, DADO ou PARSING só mescla depois de rodar a suíte no PC dele (com o
`data/interim/`), porque é lá que esses testes rodam; fases só do site (v2-6, v2-7) podem seguir na nuvem.** Os grupos:
- **Sem `data/interim/` (68):** `test_erros_casos_julgados` 15, `test_rating` 8, `test_grenade_throws` 7, `test_verdade_do_arremesso` 7,
  `test_fallbacks_declarados` 4, `test_tick_pelo_projetil` 4, `test_escada` 3, `test_grenades` 3, `test_erros` 2, `test_fixture_ci` 2,
  `test_rating_rounds_jogados` 2, `test_replay_direcao` 2, `test_timeline` 2, e 1 em `test_cegueira`, `test_dano_real`,
  `test_determinismo_em_processos`, `test_economia_reprodutivel`, `test_geometry`, `test_referencia_do_rating` (o CI usa a fixture) e
  `test_sides`.
- **Grupos/Supabase (23):** `test_grupos_integracao` 22 (parte B: projeto real e `GRUPOS_INTEGRACAO=1`; o B15 com `GRUPOS_B15_GLOBAL=1`)
  e `test_grupos_migracoes` 1 (Node e PGlite).
- **Pulados por desenho, em qualquer máquina (49):** `test_match_highlights` 47 ("destaque não é negativo nesta partida", um por
  partida) e `test_perfil_erros` 2 ("nenhum jogador com os dois níveis na partida").
- **Outros (2):** `test_visao` 1 (a malha da Mirage sai do cliente do CS2: `scripts.visao_malhas`, só no PC do Pedro) e
  `test_referencias_a_decisoes` 1 (precisa do histórico inteiro do git; o clone da nuvem e o do CI são rasos).
- Um teste do navegador varia entre 142 e 143 pulados conforme a rodada; nenhum deles é de métrica.

**v2-5b FEITA (2026-10-29):** merge `b21c773` na `main` e `dfd942d` (a palavra do papel de serviço saiu de duas notas: o
`test_grupos_config` a procura em todo arquivo e o commit da passagem a tinha escrito); CI da `main` verde e deploy `success` em
`dfd942d`. O mapa da prancheta tem um tamanho só durante a edição (sonda em 9 tamanhos de janela e nos 5 instantes da sonda dos três
momentos); decisão 2 = C (dica de 1 linha; as opções do pincel e da granada numa coluna ao lado do mapa; 343 px a 1366x768);
decisão 1 = A (referência `notas/design/referencias/v2-5b/`, idêntica byte a byte à `main` com o mapa do mesmo tamanho); o seletor de
cor da prancheta, que nunca abria, voltou a abrir (OK do Pedro); os 30 px do Reproduzir ficam como exceção da nota 48 (OK do
Pedro). 20 de 20 nos dois testes de arrasto. **Falta só:** o Pedro apagar a branch temporária `sonda-alca-ci` no GitHub (a local já
não existe).

**v2-6 FEITA (2026-10-29), merge `7a118673`:** máscaras de pontos dos 8 mapas, imagem de compartilhamento 1200x630 por partida e da
landing (53 PNG, 16 a 32 KB; `og:image:width/height` batem nas 64 páginas), esqueleto de carregamento (`?estado=carregando`, sem
porcentagem). Na nuvem: o teste instável `test_perfil_erros::test_detalhes_fecha_por_padrao_lembra_e_nao_estoura_375` (caiu no CI do
WIP da v2-5b) corrigido no site: o Perfil grava o aberto/fechado pelo `MutationObserver` do atributo `open`, e não pelo evento
`toggle`, que o navegador dispara numa tarefa depois do clique. Medido: suíte 1469 passed; impressão main x branch com 0 diferenças;
4 quadros idênticos; `docs/` +1,5 MB (184,9 para 186,4 MB; o previsto era +4 MB); build de 29,4 s para 41,2 s (39,7 s com o cache).
Prévia em `preview-v2/` (fora do git).

**v2-7 FEITA (2026-10-29), merge `73fc57d0`, CI e deploy verdes.** Medida no Pages (Fast 4G, CPU 4x, 5 medidas, cache limpo;
`notas/logs/nuvem-pages-antes.log` e `-depois.log`), antes (`165f0d00`) x depois (`73fc57d0`), LCP mediana e CLS pior:
landing 375: 0,48 s / 0,085 -> 0,78 s / 0; landing 1440: 0,63 s / 0,0004 -> 0,80 s / 0; partida 375: 0,56 s / 0,0095 -> 0,74 s / 0,0003;
partida 1440: 0,61 s / 0,082 -> 0,68 s / 0,0003; Perfil 375: 0,52 s / 0,0095 -> 0,70 s / 0,0003; Perfil 1440: 0,53 s / 0,009 -> 0,75 s / 0,0003;
prancheta 375: 2,79 s / 0,029 -> 2,02 s / 0; prancheta 1440: 2,59 s / 0,033 -> 2,04 s / 0. O LCP da landing e da partida subiu
0,15 a 0,3 s: o `font-display: fallback` espera até 100 ms pela fonte (a troca pelo CLS 0). Nenhum CLS acima de 0,01; LCP da
landing abaixo de 2,5 s. **Cartão 20 PRONTO na branch `cartao-20-biblioteca-externa` (decisão 49), esperando o OK do Pedro para o merge** (ele pediu o
LCP da prancheta antes e depois antes do merge). Medido localmente com gzip como o Pages (a `main` local reproduz o Pages: 2,06 /
2,01 s contra 2,02 / 2,04 s), Fast 4G e CPU 4x: LCP da prancheta de 2,06 / 2,01 s para 0,78 / 0,87 s (375 / 1440), CLS 0; a busca
de arremesso real pronta em 1,4 a 1,55 s (antes 2,2 a 2,3 s). Suíte 1474 passed; impressão com 0 diferenças; 4 quadros idênticos;
pranchetas sem erro no console nem rolagem lateral; CI verde. Contagem de testes 1.717.
**Cartão 17 FECHADO** (merge `165f0d00` na `main`; já mesclado nesta branch): o nick salvo do `test_grupos_convite` gravado por uma
página já aberta (script de início que toca o `localStorage` em `file://` separava o armazenamento da aba). A parte B dos grupos
continua esperando o Pedro reativar o Supabase. Cartões 6, 7 e as tarefas de dado rodam no PC do Pedro.

**v2-7, branch `v2-7-verificacao` (sem portão; o Pedro pediu as capturas dos itens 1 a 3 e a tabela do item 5 antes do merge), em
2026-10-29:** feito e com CI verde: (1) faixa com o fundo da página acima da navbar; (2) botões do Replay em pílula; (3) a moldura
do Replay (o "1×" incluído) com o escuro de antes da v2-5; (4) `preload` das fontes só por HTTP e `font-display: fallback`;
(5) CLS: o que o JS monta não empurra mais nada (invisível até montar); (6) 64 páginas x 3 larguras x cada aba sem rolagem lateral,
sem erro no console e sem e-mail, e o agente sem o cartão do jogador; (7) cartões 16 a 19 no PENDENCIAS; `aceite.py` com a Geist
Mono; imagens do README regeradas; nota 48. Impressão main x branch com 0 diferenças; 4 quadros idênticos. **Bloqueio:** a medição
no Pages (itens 4 e 5) não roda nesta sessão: a rede do ambiente nega `pedroppansani.github.io` (o Pedro libera em Network access do
ambiente). Medido por HTTP local (Fast 4G, CPU 4x): CLS 0,000 em landing, partida, Perfil, prancheta e jogadores a 375 e 1440,
com um resto de 0,0003 no cabeçalho da partida (Linux sem Arial); a fonte embutida em data URI zera, mas muda a regra das fontes e
2 testes (escolha do Pedro). Não mudou: `--f-cond` (trocar mexe na fonte dos símbolos no Linux) e o
`test_acessibilidade::test_dim_tem_contraste…` (lê o primeiro `--apagado`, o do escuro; mudar o teste precisa do OK do Pedro).

**Fila que falta, nesta ordem:** (1) ~~fechar a v2-5b~~ (feito); (2) ~~v2-6~~ (feito); (2b) ~~cartão 17~~ (feito, `165f0d00`); (3) ~~v2-7~~ (feito, `73fc57d0`; verificação final: LCP/CLS da landing no
Pages, critérios A1 a A26 e N1 a N9 do plano seção 4.8, capturas de todas as páginas em 375 e 1440 px, `README` e `assets/readme/*.png`,
`numeros_citaveis`); (3b) cartão 20 (a biblioteca de arremessos num arquivo próprio, carregado depois; decidido pelo Pedro); (4) cartão 6 (histograma da força da rota B), cartão 7 (os `.rar`: disco com 12 GB ou mais, conferir
`demos/entrada/_extraido/`, sha256 de cada `.dem`, regra 36) e cartão 9 (refatoração, com a proposta, só propor, de gerar a contagem de
testes no build); (5) parte B dos grupos (antes: pedir ao Pedro para REATIVAR o projeto Supabase e esperar a confirmação; `GRUPOS_ATIVOS`
fica `False` até o LIBERADO do agente `seguranca` e o OK do Pedro; decidir o pause do plano Free; gitleaks, npm audit, pip-audit e
`.claude/worktrees/` no `.gitignore`).

**Pendências abertas (cartões em `notas/PENDENCIAS_PARA_O_PEDRO.md`):** 14 (comparação por grupos no Perfil, fase própria depois da
v2, regra de empate do Pedro), 15 (regra de tamanho do mapa do protótipo), 16 (texto branco do protótipo no escuro, opcional), 17
(`test_grupos_convite::test_um_clique_entra_no_grupo` instável e dependente da ordem; reproduz na `main` com
`py -3.12 -m pytest tests/test_grupos_painel.py tests/test_grupos_convite.py -q -p no:cacheprovider`; resolver antes da parte B; NÃO
marcar para pular nem repetir). **Itens da v2-7 (do Pedro):** (a) ao rolar, o conteúdo aparece POR CIMA da navbar flutuante (no Perfil a
1440 px a borda do placar; a 375 px a pílula "começou TR"): ver se o espaço acima da navbar deve ter o fundo da página e mostrar antes e
depois na prévia; (b) botões do Replay (Desenhar, Direção, Abrir round na prancheta, Tela cheia, ?) em pílula, e o "1x" do Replay, que
ficou com fundo violeta: a moldura do Replay deve ficar com o escuro de antes; (c) `aceite.py`, `capturas_readme.py` e `interacao.py`
ainda procuram `btn-partida` e "JetBrains"; `--f-cond` ainda no template; `test_acessibilidade.py::test_dim_tem_contraste…` lê o primeiro
`--apagado` do `tokens.css` (o bloco escuro está primeiro); fallback da fonte mono no macOS; o `Content-Encoding` dos `.js` dos agentes
já foi conferido no Pages (gzip); (d) ~~a faixa vazia da barra de cima da prancheta~~: resolvida pela decisão 2 = C (v2-5b).

**Regras combinadas que ainda não estão num CLAUDE.md:**
- Todo comando longo (suíte, reprocesso, build, capturas, espera de CI) roda com `timeout` e saída em `notas/logs/` (fora do git), um
  comando por chamada; se passar do limite, parar e dizer qual foi. Vale também no prompt de todo agente. O CI da v2 leva até ~19 min;
  `gh run watch` pode sair com erro sem falha real: confirmar com `gh run list --branch <b>`; um push novo CANCELA o CI em andamento.
- Portões do Pedro na v2: v2-3+v2-4 e v2-5 esperaram o OK dele depois da prévia local (`preview-v2/index.html`, no `.gitignore`);
  v2-2, v2-6 e v2-7 não esperam. Toda fase gera a prévia e passa o caminho. Se um quadro do canvas do `compara_capturas` mudar, PARAR
  e levar antes e depois com o motivo. Teste fora da lista autorizada que precise mudar: parar e levar opções com recomendação.
- Teste instável: nunca marcar para pular nem repetir automaticamente; achar a causa e corrigir no site.
- Agente (subagente) termina SEMPRE com o relatório final e commita por item; o limite de sessão da API já cortou agentes duas vezes (o
  trabalho commitado fica salvo; retomar com SendMessage).
- Windows: criar a junction do `data/interim` com PowerShell `New-Item -ItemType Junction` (o `mklink` do Bash falha) e removê-la com
  `cmd /c rmdir` (nunca `rm -rf`); conferir `data/interim` com 1071 arquivos. Browser dos testes: `channel="chrome"` (o Chromium do
  Playwright não está instalado na máquina do Pedro). O `rm` de pasta pode ser barrado: sobrescrever e conferir com `diff -rq`.
- Versão das métricas na `main`: 30. `GRUPOS_ATIVOS = False`. A chave do papel de serviço ou a `sb_secret_` nunca vai ao repositório (e a palavra do papel nem é escrita: `test_grupos_config` a procura em todo arquivo). O e-mail do
  Pedro nunca aparece no site nem no README. A pasta Iriun (`C:/Users/User/Desktop/TimeIA/Iriun/`) é só leitura.

## Regras temporárias em vigor

- `GRUPOS_ATIVOS = False` (`scripts/grupos_config.py`): só vira `True` com o LIBERADO do agente `seguranca` e a
  confirmação do Pedro. A palavra do papel de serviço do Supabase não aparece em nenhum arquivo versionado (há teste).
- `TIPOS_DE_ERRO_VALIDADOS`: seis tipos na `main` (não trocou, perdeu a troca, morreu sozinho, primeira morte sem
  troca, dano de utilidade no time e flash no time, esta validada em 2026-10-21, 10/10). O possível bait fica fora
  (9 casos, abaixo de `MIN_CASOS_PARA_VALIDAR`). `FORTES_POR_LADO_PUBLICADOS = True`.
- `MIN_CASOS_PARA_VALIDAR = 10`: hoje só o "possível bait" (9 casos) fica fora.
- Merge sem confirmação só quando o prompt da fase autoriza por escrito (regra da raiz).
- Limites dos CLAUDE.md (tests/test_claude_md.py): raiz 15.000 no teste e meta 10.000; `metrics/` 12.000;
  `scripts/` e `dashboard/web/` 6.000; as outras pastas, inclusive `metrics/erros/`, 5.000. Se um precisar passar
  do limite, não suba de novo: pare e traga uma proposta de divisão.
- A branch `fase-6-decisivo` e as tags `baseline-*` não são apagadas.
- **Portões da v2 (Pedro, 2026-10-25):** v2-3 + v2-4 (landing e páginas claras, juntas) e v2-5 (prancheta) ESPERAM o OK
  do Pedro depois da prévia local (`preview-v2/index.html`) e antes do merge; eu mando o caminho e uma lista curta do que
  conferir. v2-2, v2-6 e v2-7 seguem sem esperar. Em toda fase da v2 há prévia local.
- Comando longo (suíte, reprocesso, build, capturas): um por chamada, com `timeout` e a saída em `notas/logs/`
  (fora do git); se passar do limite, parar e dizer ao Pedro qual foi (pedido dele, 2026-10-24).
- Dados: `data/interim` e `demos/` só por junction de leitura nos worktrees, removida no fim (regra 36). O
  reprocesso grava caminhos absolutos de demo no `data/manifest.json`: restaurar `caminho` e `existe` (só versão,
  commit, data e `sujo` podem mudar).
- Versão das métricas na `main`: 30 (cartão 5, tick pelo projétil na FACEIT; a 29 foi a referência do rating).
- **Supabase (resposta do Pedro, 2026-10-21):** push protection ligado no GitHub e plano Free sem cartão. O projeto
  `parser-cs2-grupos` está PAUSADO por inatividade (o Free pausa depois de 7 dias sem uso). **(1) A parte B está
  destravada, mas antes de começar ela eu peço ao Pedro para reativar o projeto e espero ele confirmar.** A ordem
  não muda: a parte B fica para DEPOIS da v2-7. **(2) Pendência para a revisão de segurança:** no Free o projeto
  pausa depois de 7 dias sem uso, então os grupos no ar podem parar se ninguém usar; isso precisa de uma decisão
  do Pedro antes de ligar o `GRUPOS_ATIVOS`.

## Feito (merges na `main`, todos com CI verde)

| item | merge |
|---|---|
| Fase 11: granadas como desenho | `977e3da5` |
| Fase 12: erros na aba Perfil | `9b1b108a` |
| Fase 13: grupos na prancheta (desligados) | `190a0f0e` |
| Fase 12b: referência por lado e função, convite ao mapa certo, glossário | `af3b7533` |
| Fase 15: componentes do design (§19) | `5aa4ab00` |
| Fase 14: CLAUDE.md por pasta | `fb2a81bb` |
| Fase 16a: pendências da fase 15 | `cc2b7242` |
| Fase 16b: correções de segurança dos grupos | `6739b475` |
| Fase 17a: regras, notas, material, teste de rede, cópias entre pastas | `542b9363`, `eb54ac93`, `fcce4c98` |
| Fase 17: ponto atrasado, contador, sem `CAMINHO_POR_CLIQUE` | `e7a02092`, `f0e0ad11`, `48fcd6b5` |
| Fase 17: roteiro do NVDA (cartão 11) e intervalo de 95% | `4f0c3c94` |
| Fase 18: tipos de erro revistos (visão, troca pelo fato, round decidido) | `d02b0e7e` |
| `metrics/CLAUDE.md` com limite 12.000 | `b3efc9da` |
| Fase 17: Galil/FAMAS (fica em força) | `ce576956` |
| Fase 17: cartão 8 (branches apagadas) | `f7b78968` |
| Fase 17: cartões 2, 3 e 4 | `36a991bf` |
| Fase 18b: calibração dos erros, bait com amostra insuficiente | `921aa334` |
| "Quanto cada round pesou" no lugar da curva repetida | `16749e2e` |
| Fase 17: degrau 4b da escada (assistência de flash; não bate) | `4a48c75f` |
| Tickrate lido da demo na flash e na utilidade (versão 26, cartão 12) | `a7db5dc9` |
| Divisão do `metrics/CLAUDE.md` (`metrics/erros/CLAUDE.md`) | `0f487a09` |
| `notas/estado-atual.md` criado | `f138103c` |
| Calibração, item 2: grupos de estilo (nomes pelo perfil; o reajuste reproduz o modelo) | `3c4afd79` |
| Calibração, item 3: cinco tipos de erro validados, `MIN_CEGUEIRA_FLASH_ALIADO`, versão 27 | `7775cd27` |
| Flash no time validada (10/10) e no Perfil | `33a9159d` |
| Calibração, item 1: pisos de função (suporte 40 s, versão 28; 21 jogadores mudam de função na `jogadores.html`, nota 31) | `d5562e76` |
| Cartão 13: referência do rating regravada e presa por teste (byte a byte no Windows, 1e-12 no CI), versão 29 | `2d547d7b` |
| Cartão 5: tick da soltura pelo projétil nas demos da FACEIT (piora 0, +447 botões, 2.390 comandos mudam), versão 30 | `4f1407a7` |
| v2-1 (base da GOAT.demo): fontes Geist no site, tokens em dois temas (o site fica no escuro de hoje), CSP sem Google Fonts, nota 48 | `abe79b27` |
| v2-2 (marca): cabra C e wordmark, favicon, títulos "· GOAT.demo · Replay de CS2", README | `d67f831e` |
| v2-3 + v2-4 juntas (OK do Pedro após a prévia): navbar flutuante, landing no claro com agente, partida e jogadores no claro, abas gooey, moldura do mapa, Perfil em pílulas | `52bafe77` |
| v2-5 (prancheta no escuro violeta; mapa da prancheta 27 px menor por causa da navbar, só tamanho) | `c3f63a73` |
| v2-5b (mapa da prancheta com um tamanho só na edição; decisões 1 = A e 2 = C; seletor de cor; CI da `main` verde de novo) | `b21c7732`, `dfd942d7` |
| v2-6 (pontos de todos os mapas, imagem de compartilhamento por partida, esqueleto de carregamento; Perfil sem o teste instável) | `7a118673` |
| Cartão 17 (o `test_grupos_convite` sem falha ao acaso) | `165f0d00` |
| v2-7 (verificação final: navbar, Replay, fontes, CLS 0, conferência, cartões 16 a 20) | `73fc57d0` |
| `fix-tickrate-resto`: tickrate lido da demo em todo lugar, sem mudar nenhum número (sha256 dos dados igual ao da `main`); contagem de testes 1.678 | `47c0f840` |

## Em andamento

Nada. Pendências da v2 já anotadas nos cartões 14 e 15 de `notas/PENDENCIAS_PARA_O_PEDRO.md`:

- Cartão 14: comparação por grupos no Perfil (fase própria depois da v2, regra de empate do Pedro). Cartão 15: regra de tamanho
  do mapa do protótipo (muda os pixels dos 3 quadros do Replay).
- Para a v2-7: `aceite.py`, `capturas_readme.py` e `interacao.py` ainda procuram `btn-partida`/"JetBrains"; `--f-cond` ainda no
  template; `test_acessibilidade.py::test_dim_tem_contraste…` lê o primeiro `--apagado` do `tokens.css` (o bloco escuro está
  primeiro); `Content-Encoding` dos `.js` dos agentes no Pages; fallback da fonte mono no macOS.
- **Pedido do Pedro para a v2-7 (2026-10-27), 2º ponto:** os botões do Replay (Desenhar, Direção, Abrir round na prancheta,
  Tela cheia, ?) continuam quadrados; avaliar deixá-los em pílula, como a barra de ferramentas da prancheta.
- Cartões novos nas pendências: 16 (texto branco do protótipo no escuro, opcional) e 17 (`test_grupos_convite::test_um_clique_entra_no_grupo`
  instável e dependente da ordem; resolver antes da parte B; não marcar para pular nem repetir).
- **Pedido do Pedro para a v2-7 (2026-10-27), 1º ponto:** ao rolar, o conteúdo aparece POR CIMA da navbar flutuante (no Perfil a 1440 px
  dá para ver a borda do placar; a 375 px, a pílula "começou TR"). Ver se o espaço acima da navbar deve ter o fundo da página
  e mostrar o antes e depois na prévia da v2-7.

## Fila (na ordem; o Pedro mudou em 2026-10-24)

1. A v2 (GOAT.demo), v2-1 a v2-5 FEITAS (próxima: v2-6 pontos e imagem de compartilhamento, sem portão; depois v2-7), plano aprovado em `C:/Users/User/Desktop/Claude outputs/PLANO-v2-0.md`: v2-1 base (não
   muda a aparência; o escuro atual vira `data-tema="escuro"`), v2-2 marca, v2-3 e v2-4 em sequência numa branch de
   integração e para a `main` no mesmo push, v2-5 e v2-6 em paralelo depois de a v2-4 mesclar o `map_core.js`, v2-7
   verificação final. Condições de cada fase: suíte verde, impressão dos números idêntica, só as capturas e os
   testes autorizados mudam. Dúvidas do plano respondidas (todas as recomendações aceitas); só os testes de visual
   da seção 4.4 podem mudar; o `scripts/CLAUDE.md` não ganha linha (se precisar, parar e propor divisão). **A cada
   fase, uma prévia local: o site da branch em `preview-v2/` (no `.gitignore`), e o caminho do `index.html` no
   relatório, para o Pedro testar no navegador antes do merge.** Na v2-7: pôr no PENDENCIAS o `curl` do
   `Content-Encoding` dos dois agentes depois do deploy e o fallback da fonte mono no macOS. Fase própria depois
   da v2: a comparação por grupos do Perfil, com a regra de empate do Pedro.
2. Depois da v2-7: cartão 6 (histograma da força da rota B), cartão 7 (os `.rar`: espaço em disco ≥ 12 GB,
   `demos/entrada/_extraido/` conferida antes, sha256 de cada `.dem`, regra 36) e cartão 9 (a refatoração, com a
   proposta, só propor, de gerar a contagem de testes no build pela coleta do pytest). A refatoração passou para
   depois da v2 por decisão do Pedro; ela continua tendo de provar que nenhum número muda.
3. Parte B dos grupos, DEPOIS da v2-7 e só depois de o Pedro reativar o projeto Supabase e confirmar (ver as
   regras temporárias). Junto: plano Free, a maior tática real (máximo, mediana e p95 de operações), `gitleaks`,
   `npm audit` e `pip-audit`, e o `.claude/worktrees/` no `.gitignore`; depois o `grupos.md` para o `seguranca`.
4. Do lado do Pedro: o dano de utilidade na escada (cartão 1, prints da HLTV); o roteiro do NVDA (cartão 11); o
   cartão 10 (Supabase); a fase 6 (`fase-6-decisivo`); a investigação do awpy 3 fica numa sessão separada.
