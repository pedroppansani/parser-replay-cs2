# Estado atual do trabalho (para abrir uma sessão limpa)

Atualizado em 2026-10-28 (passagem para a nuvem: ver a seção logo abaixo). Os prompts de origem citados estão em
`C:\Users\User\Desktop\Claude outputs\` (os mais antigos já não estão no disco; o que eles pediram está nos cartões
de `notas/PENDENCIAS_PARA_O_PEDRO.md` e nas notas de decisão).

## Passagem para a nuvem (2026-10-28): LEIA ESTA SEÇÃO PRIMEIRO

O Pedro passou o projeto para uma sessão na nuvem. Só vale o que está no GitHub. O plano da v2 e as respostas do Pedro foram
copiados para `notas/design/v2/` (`PLANO-v2-0.md`, `PROMPT-MESTRE-fila-do-projeto.md`,
`PROMPT-respostas-v2-0-e-pendencias.md`, `LISTA-O-QUE-FALTA.md`); onde este arquivo cita `C:/Users/User/Desktop/Claude outputs/`,
use a cópia daqui. Relatórios ao Pedro em linguagem simples (ele lê no celular).

**O que está na `main` (a6b738e0):** v2-1, v2-2, v2-3, v2-4 e v2-5 mescladas (ver "Feito"). **O CI da `main` está VERMELHO** em
2 testes de navegador da prancheta (`test_desfazer_e_refazer_voltam_ao_estado_exato_em_cada_operacao`, falha 20 de 20 no Linux;
`test_girar_pela_alca_ate_90_aponta_para_cima`, ~3 de 20), por causa da v2-5. O site publicado continua na v2-3/v2-4 (o deploy só
roda com testes verdes). Nenhuma outra fase entra na `main` enquanto ela estiver vermelha.

**A correção, branch `v2-5b-mapa-estavel`** (no GitHub; o último commit é um WIP: "falta aplicar decisão 2"):
- Causa (medida no Linux): ao selecionar a peça, a linha de dica (`#pr-dica-estado`) troca para um texto longo, quebra em 2 linhas
  sem a Geist, o mapa desce 15 px sem reprojetar e o clique cai fora da peça (raio de acerto ~7 px). Outras duas fontes: a linha do
  tempo (`#pr-linha`) crescia +50 px por jogador e escolher ferramenta de desenho punha +50 px na barra de cima; o mapa mudava de
  tamanho a cada criar/desfazer/refazer.
- Já feito: `7bdb6149` (mapa estável: `reprojeta()` desconta reservas fixas, `ResizeObserver` também na barra, na dica, no cabeçalho e
  na navbar, `document.fonts.ready` reprojeta), `7e08e2c9` (dica de 49 px; 67 no celular; 109 com grupo; nota 48), `87b2104a` (altura
  reservada da barra). No Linux, 20 de 20 nos dois testes e 20 de 20 no controle e94bba68 (branch temporária `sonda-alca-ci`, workflow
  `.github/workflows/sonda-alca.yml`, ref `7bdb61493ee0c4155911338cf2856f5c75c77269`). Os testes NÃO mudaram (regra do Pedro: a
  correção é no site; nada de pular, nova tentativa automática ou tolerância maior).
- **Decisões do Pedro (2026-10-28):** **Decisão 1 = A:** gravar a referência nova do `prancheta_fixture_p2` (453 para 457 px a 1300x950;
  com o mapa no mesmo tamanho a GPU dá 20.416 pixels diferentes só nas bordas do radar, no máximo 29/255) num commit PRÓPRIO, com a
  prova: com o canvas em software (`--disable-accelerated-2d-canvas`) o conteúdo do canvas da `main` e o da branch são idênticos byte a
  byte; os 3 quadros do Replay seguem idênticos. **Decisão 2 = C:** dica de 1 linha com reticências no computador e ELIMINAR a faixa
  reservada da barra de cima (as opções do pincel e da granada desenhada passam a aparecer sem empurrar o mapa); o espaço reservado da
  linha do tempo fica ("Os passos aparecem aqui"). Tamanho do mapa com a correção atual, sem a decisão 2: 275 px a 1366x768 (era 394),
  407 a 1440x900, 456 a 1300x950, 343 no celular; a decisão 2 recupera cerca de 69 px. O mapa tem de continuar inteiro, sem rolar, a
  1366x768.
- **Falta:** aplicar a decisão 2; gravar a referência (decisão 1); suíte inteira; impressão dos números main x branch (0 diferenças);
  busca de e-mail no HTML; contagem de testes (`py -3.12 -m scripts.numeros_citaveis`); CI verde; prévia em `preview-v2/` (caminho do
  `index.html` ao Pedro) e captura 1366x768; repetir no Linux as 20 repetições dos 2 testes (precisa dar 20 de 20; se o do giro falhar
  alguma vez, parar e levar ao Pedro). "Reproduzir" troca a dica pela barra do player (mais alta): o mapa desce ~12 px no computador
  durante o modo (anotado na nota 48, aceito). **Com tudo verde: mesclar na `main`, conferir o CI e o deploy, apagar a `sonda-alca-ci`
  (GitHub e local) e só então liberar a v2-6.**

**v2-6, branch `v2-6-pontos-og` (`d711d90b`, no GitHub; CI verde em `dd4bdc92`; fase SEM portão do Pedro):** feito: máscaras de pontos de
todos os mapas, imagem de compartilhamento 1200x630 por partida e para a landing (Pillow, fontes estáticas em `scripts/design/fontes_og/`),
`og:image` por página, esqueleto de carregamento (`?estado=carregando`, sem porcentagem), nota 48, contagem 1.714; impressão com 0
diferenças e 4 quadros idênticos. **Falta:** mesclar a `main` nova (depois da v2-5b) e rodar suíte e CI; olhar as capturas (estavam em
`C:/Users/User/Desktop/Claude outputs/capturas-v2-6/`, que não está no repositório: gerar de novo); medir `docs/` antes e depois (cerca
de +4 MB) e o tempo do build (31,7 s); gerar a prévia; relatório final; mesclar.

**Fila que falta, nesta ordem:** (1) fechar a v2-5b e mesclar (main verde); (2) v2-6; (3) v2-7 (verificação final: LCP/CLS da landing no
Pages, critérios A1 a A26 e N1 a N9 do plano seção 4.8, capturas de todas as páginas em 375 e 1440 px, `README` e `assets/readme/*.png`,
`numeros_citaveis`); (4) cartão 6 (histograma da força da rota B), cartão 7 (os `.rar`: disco com 12 GB ou mais, conferir
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
já foi conferido no Pages (gzip); (d) a faixa vazia da barra de cima da prancheta é resolvida pela decisão 2 = C.

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
