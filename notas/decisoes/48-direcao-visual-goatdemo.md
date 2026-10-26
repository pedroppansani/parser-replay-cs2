# Decisão 48: Direção visual v2 "GOAT.demo"

- **ID:** 48
- **Status:** vigente
- **Data:** 2026-10-25
- **Resumo:** O site ganha a direção v2 "GOAT.demo" em fases (v2-1 a v2-7). Dois temas por página (`<html data-tema="claro|escuro">`), o mapa sempre escuro e lido pelos tokens `*-mapa`, as fontes Geist e Geist Mono hospedadas no próprio site (sem Google Fonts) e a CSP sem origem externa de estilo nem de fonte. Revê a decisão 44 no tema único, nas fontes e no Google Fonts; o resto da 44 continua valendo.

## Texto

48. **Direção visual v2 "GOAT.demo"** (plano `C:/Users/User/Desktop/Claude outputs/PLANO-v2-0.md`, aprovado pelo
Pedro em 2026-10-24, todas as recomendações aceitas). A especificação do design (feita por outro agente) está
copiada em [`notas/design/entrega-v2-goatdemo.md`](../design/entrega-v2-goatdemo.md), e é essa cópia que vale
dentro do projeto; os tokens do protótipo ficam em `notas/design/prototipo-v2/tokens.css` (referência, não entra
no build). Como na 44, o documento dá a FORMA: onde ele pedir comportamento novo, vale o do main e o conflito vai
para o relatório, e cada fase deixa zero diferença numérica (`scripts/design/impressao_numeros.py`).

**O que a 48 revê da 44:** o tema único escuro (agora há dois temas por página), as fontes Archivo e JetBrains
Mono (agora Geist e Geist Mono) e o Google Fonts como única CDN (agora nenhuma). Continuam da 44: uma cor, um
papel; o radar dessaturado e o anel duplo; as granadas e as suas formas; o mapa em canvas; o `--f-codigo` (mono
do SISTEMA para o comando que se copia, dúvida 6 do plano, opção B). "Página da partida sem o topo do site" muda
na v2-4.

**Regras (valem para todas as fases da v2):**

- **Tema por página.** `tokens.css` tem o bloco `:root, [data-tema="claro"]`, o bloco `[data-tema="escuro"]` e
  um `:root` com o que é igual nos dois (mapa, tipografia, forma). Toda página declara o tema no `<html>`.
  O escuro é `:root[data-tema="escuro"], [data-tema="escuro"]`, que pesa mais que o `:root` e vale em
  qualquer ordem; na v2-1 ele vem primeiro no arquivo. Na v2-1 todas ficam em `data-tema="escuro"`, que é o escuro de hoje (Sala de demo) com o nome novo: o site
  não muda de cor. O claro entra quando uma página inteira estiver pronta (v2-4); o escuro violeta da prancheta
  na v2-5 (nesse dia o bloco escuro troca de valores).
- **O mapa é sempre escuro.** O canvas (`map_core.js`, `tactics.js`, `annotations.js`) lê só `tinta-mapa`,
  `tinta-2-mapa`, `apagado-mapa`, `foco-mapa`, `fundo-mapa` (e `ct-mapa`, `tr-mapa`, `aviso-mapa` quando o
  código passar a usá-los) e as granadas, todos no `:root` comum, com os valores escuros de hoje: no tema claro
  `--tinta` é `#0a0a0a` e sumiria sobre o radar (1,07:1). O `tinta-mapa` fica no `#e8edf2` de hoje, e não no
  `#ffffff` do protótipo, para nenhum pixel do mapa mudar de cor.
- **Paleta por tema.** `py -3.12 -m metrics.paleta` dá três saídas (claro, escuro e mapa), fixadas em
  `tests/fixtures/paleta_<tema>_saida.txt`; o mapa também confere que os tokens do canvas são iguais nos dois
  temas. `le_tokens()` lê pela cascata do CSS, no tema das páginas (`TEMA_DAS_PAGINAS`, hoje "escuro").
- **Fontes.** Geist e Geist Mono (OFL 1.1, pacote npm `geist` 1.7.2), woff2 com subconjunto latino, eixo
  wght de 400 a 600, versionados em `dashboard/web/fontes/` com o `OFL.txt`. Os dois `@font-face` saem de
  `scripts/design_head.fontes_html()` (marcador `<!--__FONTES__-->`) com `url(fontes/…)`; os 4 `@font-face`
  de fallback medidos ficam no `tokens.css`. Sem `<link rel=preload crossorigin>` (em `file://` o CORS o
  bloqueia). O peso mais forte é 600 (`--peso-forte`), porque a fonte não tem 700. A Geist não tem largura
  condensada: onde a Archivo a 75% cabia em 375 px (título da prancheta, as quatro abas do painel), o CSS
  deixa encolher ou tira o espaçamento no celular.
- **Build.** `scripts/build_site.py` copia `dashboard/web/fontes/` para `fontes/` ao lado das páginas
  (`docs/` e `preview/`, por `design_head.copia_fontes`); `scripts/compara_capturas.py` faz o mesmo nas páginas
  que gera. `scripts/design/gera_fontes.py` (precisa do `fontTools`) e `scripts/design/mede_fallback.py`
  (precisa do Chrome) entram no repositório mas NÃO rodam no build nem nos testes.
- **CSP** (`scripts/csp.py`): `style-src 'self' 'unsafe-inline'` e `font-src 'self'`, sem nenhuma origem externa.
- **Autocontida.** A pasta `docs/` abre sem rede (melhor que antes, que precisava do Google). Um HTML solto,
  copiado sem a pasta `fontes/`, cai no fallback medido (teste `test_fontes_file_browser`).

**Marca (v2-2).** `dashboard/web/marca/` tem só a cabra C, o `goatdemo.svg` (com a mira, de 24 px para cima) e o
`goatdemo-liso.svg`, gerados por `scripts/design/gera_marca.py` (não roda no build). O favicon é a cabra C em
`#0a0a0a` (`scripts/meta_da_pagina.FAVICON`), todo `<title>`/`og:title` termina em `MARCA` ("GOAT.demo · Replay
de CS2") e o topo atual mostra o wordmark liso a 17 px. Nada de agente, Valve ou CS2 na marca. A `og:image`
continua `replay.png` até a v2-6.

**Landing e navbar (v2-3).** Regras de build que a v2-3 deixou:
- O CSS novo da v2 mora em `dashboard/web/v2.css` e entra pelo marcador `/*__V2__*/` (`design_head.aplica`), nunca no
  `template.html`; o comportamento comum (`--nav-h`, foco abaixo da navbar, `<dialog>`) em `dashboard/web/v2.js`, inline.
  Na v2-3 só a landing tem o marcador; jogadores e prancheta recebem a marcação nova do `topo_do_site` (cabra C, três
  links, sem GitHub) com o CSS delas, e a altura do topo não muda (o canvas da prancheta fica igual). A v2-4 e a v2-5
  põem o marcador nas outras páginas.
- Os textos da landing saem de `scripts/build_site.TEXTOS_DA_LANDING` (decisão 18); os três números e a linha do corpus,
  do `numeros_citaveis.json` (37). A partida de exemplo (`partida_de_exemplo`, mesmo critério) é o primeiro card, em
  destaque (`data-exemplo`); as classes dos cards ficaram as mesmas, e `impressao_da_landing` dá as mesmas linhas.
- O agente: `dashboard/web/agente/agente-{tr,ct}.js` e os quadros fixos (`-text` no `.gitattributes`), com o sha256 em
  `dashboard/web/agentes.manifesto.json` (teste `test_agente.py`); o build copia só os `.js` para `agente/`; o tocador
  (`dashboard/web/agente.js`) e o sorteio vão inline; `?agente=ct|tr` força o lado. `scripts/converte_agente.py` não roda no
  build, nenhum teste o importa e ele recusa corte de privacidade acima de y 590 (TR) e 545 (CT).
- Os pontos das laterais (Mirage e Dust II) saem de `scripts/design/gera_pontos.mascara`, que lê o radar do `.json` (o PNG
  não existe no CI), no build, em `data:` dentro do CSS; determinístico (teste `test_gera_pontos.py`).
- A captura do replay (`replay.png`) continua só como `og:image` (até a v2-6); `replay.webp` deixou de existir.
- A landing sai no claro (`TEMA_DA_LANDING`); as outras páginas seguem no escuro até a v2-4 e a v2-5, que vão ao ar
  junto com a v2-3 (o site nunca fica meio claro, meio escuro no ar).

**Medido na v2-1 (2026-10-25, Chrome no Windows, `file://`):** com a CSP do site, a Geist e a Geist Mono chegam
a `loaded` na landing, numa partida e na prancheta, sem violação; com `font-src 'none'` (controle) as duas são
bloqueadas e a violação aparece. Um `<script src="agente/agente-tr.js">` criado pelo JS depois da carga também
CARREGA em `file://` com `script-src 'self' 'unsafe-inline'` (a de hoje), sem violação: o agente da v2-3 não
precisa de CSP mais frouxa.

**Ficou para as próximas fases:** a escala tipográfica, o `--dur` de 220 ms e os raios do protótipo (os tokens
de forma novos já existem, sem uso); `--f-cond` (aponta para a Geist até a v2-4 tirar o uso); a linha do
`'DM Sans'` em `map_core.js` (sobra antiga, conferir no A6); o `template.html` ainda lê `--tinta`, `--fundo` e
os outros do tema para o canvas do replay e os gráficos (v2-4, junto com a página clara); `ct`/`tr` do canvas
da prancheta para `ct-mapa`/`tr-mapa` (v2-5); `scripts/design/aceite.py` ainda procura `JetBrains` (v2-7).
