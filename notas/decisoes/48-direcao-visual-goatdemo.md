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
foi o `replay.png` até a v2-6 (agora é a imagem de compartilhamento, ver v2-6).

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
- A captura do replay (`replay.png`) ficou só como `og:image` até a v2-6, que a trocou pela imagem de compartilhamento; `replay.webp` deixou de existir.
- A landing sai no claro (`TEMA_DA_LANDING`); as outras páginas seguem no escuro até a v2-4 e a v2-5, que vão ao ar
  junto com a v2-3 (o site nunca fica meio claro, meio escuro no ar).

**Páginas claras (v2-4).** Regras de build e de forma que a v2-4 deixou:
- A partida (`template.html`) e `jogadores.html` saem em `data-tema="claro"`, com a navbar de `topo_do_site` (a partida
  passa a ter o topo do site, o que a 44 não tinha; atual = "partida", sem `aria-current`). As duas têm o marcador
  `/*__V2__*/` no FIM do `<style>` (o CSS da v2 vem por último e ganha das regras de antes) e `<script>/*__V2_JS__*/</script>`,
  trocado pelo `build_web_page`/`build_jogadores` antes de o dado entrar. Ids e classes de antes ficam (os testes clicam neles).
- Abas: a bolha (`.goo .bolha`) e o filtro `#goo` são estrutura do template; o `v2.js` só observa o `aria-selected`
  (a troca de aba continua no JS da página) e liga `.movendo` por 220 ms; em repouso o `filter` é `none`; com reduzir
  movimento, nada de filtro. As abas grudam em `top: calc(var(--nav-h) + 4px)`.
- A moldura do mapa é o `#palco` com `data-tema="escuro"`: uma ilha do tema escuro (o texto, a legenda, o transporte e a
  barra da anotação leem o escuro), fundo `--radar`, raio 20 e o anel de 6 px da `--superficie` DA PÁGINA (a variável
  `--anel` é lida no `.stage`, fora da ilha). **Na v2-5, quando o bloco escuro virar o violeta, a ilha muda junto:
  conferir a moldura da partida nesse dia.** O canvas mantém o tamanho de antes (`max-width` 520 px): a regra
  `min(100%, 640px, 100svh − reserva)` do protótipo mudaria todos os pixels dos quadros do `compara_capturas`.
  O Pedro decidiu (2026-10-26): o mapa fica no tamanho de hoje; a regra do protótipo é o cartão 15 das pendências.
  O topo da partida ficou mais justo (só espaçamento) para o mapa inteiro e a barra de tocar caberem em 1440 x 900;
  o "Como é conferido" do Perfil leva à Metodologia do rodapé da própria página (`#foot`), sem link externo.
- O canvas do replay e a legenda dos glifos leem `CM` (`ct-mapa`, `tr-mapa`, `tinta-mapa`, `tinta-2-mapa`,
  `apagado-mapa`); os gráficos e a página continuam no `C` do tema.
- Perfil: só a forma (seletor em pílulas, bloco "em validação" tracejado). A comparação por grupos com "quem está à
  frente" é fase própria depois da v2 (cartão 14 das pendências); o mini-radar fica fora da v2.
- Saiu de `map_core.js` o nome `'DM Sans'` do texto anotado (nunca carregado nem instalado; o texto já caía no
  `system-ui`, mesmo pixel).

**Prancheta no escuro violeta (v2-5).** Regras de build e de forma que a v2-5 deixou:
- O bloco `[data-tema="escuro"]` do `tokens.css` tem os valores do escuro violeta (entrega §2.1), menos o `--tinta`, que
  fica no `#e8edf2` de antes (o `tests/test_v2_paginas.py` o compara com o `--tinta-mapa`; o `#ffffff` do protótipo é
  escolha do Pedro). Os lados, os estados e todos os `*-mapa` não mudam. `--quente-1`, `--quente-2` e `--quente-ink` só
  existem no escuro e só pintam o "Reproduzir" (`#pr-reproduzir`), uma vez por tela; o `metrics.paleta` mede o
  `--quente-ink` contra as duas pontas do degradê.
- A ilha `data-tema="escuro"` da partida (a moldura do mapa) ficou violeta junto (o anel continua a `--superficie` clara);
  atrás dos cantos arredondados do canvas fica o `--entorno-mapa` (`#121820`, a superfície escura de antes), para os 3
  quadros do Replay do `compara_capturas` seguirem idênticos (pedido do Pedro: o violeta é só da prancheta, o canvas não muda).
- `tactics.html` tem o marcador `/*__V2__*/` no fim do CSS e `<script>/*__V2_JS__*/</script>` DEPOIS do `Prancheta.init`
  (o `v2.js` acha as abas do painel já montadas); o filtro `#goo` é estrutura da página e a bolha (`.goo .bolha`) é posta
  pelo `montaLateral`. Todo CSS da prancheta no `v2.css` é preso a `.grade`/`.pr-cab`: a barra de desenho da partida
  não muda. Ids e classes de antes ficam (os testes clicam neles).
- A moldura (`.palco`) tem raio 20 e a barra de cima e a linha do tempo acompanham; o canvas mantém o raio e as cores
  (lê `ct-mapa`/`tr-mapa` desde a v2-5) e muda de tamanho só porque a navbar flutuante ocupa mais altura. O relógio
  grande vai a 42 px acima de 640 px (32 px no celular, como antes).
- A navbar, o cabeçalho e a grade da prancheta têm a largura e a margem da partida (1156 px de conteúdo; 16 px de cada
  lado no celular), pedido do Pedro; só a margem do lado muda, o mapa não muda de tamanho por isso. Com a navbar o mapa
  do quadro `prancheta_fixture_p2` (janela 1300 x 950) passou de 480 a 453 px (aceito pelo Pedro: escolha A); com a
  janela de 977 px, do mesmo tamanho, é idêntico pixel a pixel. A 1366 x 768 o mapa cabe inteiro sem rolar.
- `.ponto-status` (o ponto de online/offline do Grupo, com a palavra ao lado): online cheio em `--decisivo`, offline vazio.

**Pontos, imagem de compartilhamento e carregamento (v2-6).** Regras de build que a v2-6 deixou:
- Máscaras: `scripts/design/gera_pontos.mascara` serve todo mapa com partida no corpus (os 8 de hoje; teste
  `test_gera_pontos.py` com os 8), com cache por mapa no build. As laterais da landing seguem Mirage e Dust II (`LATERAIS`).
- Imagem de compartilhamento 1200x630 (dúvida 7: uma por partida, com o placar) e uma da landing, geradas no build por
  `scripts/design/gera_og.py` em Pillow (sem navegador: o job de build do CI só instala o `requirements.txt`), em `og/`
  ao lado das páginas (`build_site.gera_imagens_og`). A da partida traz os dois times e os pontos (quem perdeu em
  `--tinta-2`, como o card da landing), o mapa e o evento (ou FACEIT) e a frase do decisor: nada que o card da landing
  não mostre. A da landing traz o título de `TEXTOS_DA_LANDING` e a frase `og_frase`, com o Dust II (lateral direita).
  Texto com as instâncias estáticas da Geist 600/400 e da Geist Mono 500 em `scripts/design/fontes_og/` (geradas uma vez
  por `gera_fontes.py`, OFL junto; o `fontTools` não entra em nenhum requirements); a marca é o `marca_og.png`
  versionado (`gera_og --marca` o refaz com o Chrome, fora do build). Determinística, sem bloco de metadado no PNG
  (teste `test_og.py`); cerca de 25 KB cada, abaixo dos 70 a 95 KB estimados no plano por causa da paleta de 64 cores.
- `og:image` (`scripts/meta_da_pagina`): a partida aponta para `og/<partida>.png`; a landing, jogadores e a prancheta
  para `og/landing.png` (`IMAGEM_OG`), com `og:image:width/height`. O build não copia mais o `replay.png`.
- Carregamento (dúvida 5, opção B): o build põe no marcador `<!--__CARREGANDO__-->` do `template.html` (logo depois do
  `#map`) o esqueleto `#carregando` com a máscara do mapa da partida e a frase `TEXTO_CARREGANDO` do
  `build_web_page`, sem porcentagem. Fica por cima do canvas (absoluto, sem ocupar lugar; CSS no `v2.css`) e o `v2.js`
  o esconde quando a página termina de carregar; `?estado=carregando` o deixa na tela (teste e captura). O canvas, o
  tamanho do mapa e os pixels dos quadros do `compara_capturas` não mudam.

**O mapa da prancheta parado durante o uso (v2-5b, pedido do Pedro).** Na `main` da v2-5 o CI Linux falhava no desfazer/refazer
e no giro pela alça: entre o `mouse.move` e o `mouse.down` a seleção trocava o texto da linha de dica, que sem a Geist (Linux)
quebrava em duas linhas e descia o mapa 15 px sem reprojetar; a linha do tempo crescia 50 px a cada jogador (o mapa encolhia a
cada criar, desfazer e refazer) e as ferramentas de desenho punham uma linha a mais na barra (+50 px). Regras:
- Nada acima do mapa muda de altura com seleção, ferramenta ou peça (decisão 2 = C do Pedro, 2026-10-28): a dica tem UMA
  linha no computador (31 px; três no celular), o excesso em reticências, com o texto inteiro no `title` só quando corta
  (`tituloDaDica`; o `role=status` lê tudo); a barra não reserva nada: as opções do pincel (cor, espessura) e da granada
  desenhada (o tipo) saíram dela para a coluna `#pr-opcoes`, na borda direita da tela, ao lado do mapa (espelho do relógio,
  à esquerda). A coluna tem largura fixa no `v2.css` e existe mesmo invisível (`.vazia`); `reprojeta()` deixa a folga dela
  (`FOLGA_DAS_OPCOES_PX`) e o mapa nunca passa por baixo: centrado, e só anda para a esquerda quando a sobra de cada lado é
  menor que a folga. No celular não há desenho à mão: ela não aparece e não reserva nada. No Tab, ela vem logo depois da
  barra. Mapa a 1366 x 768: 343 px (era 275 com a faixa reservada; 329 na `main` da v2-5, que mudava a cada clique).
- A linha do tempo reserva desde o carregamento a altura com a primeira peça (`min-height` de 117 px no `v2.css`), com a
  frase de `build_tactics_page.TEXTOS_DA_PRANCHETA` ("Os passos aparecem aqui") no lugar da primeira faixa; `reprojeta()`
  desconta a reserva, nunca a altura de agora; com mais jogadores ela cresce para baixo do mapa.
- O `ResizeObserver` vigia a tela, a barra, a dica, o cabeçalho e a navbar, e `document.fonts.ready` pede uma reprojeção.
- Fica de fora: Reproduzir troca a dica (31 px) pela barra do player (61 px), e o mapa desce 30 px e fica 30 px menor até
  "Editar", quando volta ao mesmo tamanho e lugar (nada é editável nesse tempo; na `main` da v2-5 ia de 329 a 430 px).

**Medido na v2-1 (2026-10-25, Chrome no Windows, `file://`):** com a CSP do site, a Geist e a Geist Mono chegam
a `loaded` na landing, numa partida e na prancheta, sem violação; com `font-src 'none'` (controle) as duas são
bloqueadas e a violação aparece. Um `<script src="agente/agente-tr.js">` criado pelo JS depois da carga também
CARREGA em `file://` com `script-src 'self' 'unsafe-inline'` (a de hoje), sem violação: o agente da v2-3 não
precisa de CSP mais frouxa.

**Ficou para as próximas fases:** a escala tipográfica, o `--dur` de 220 ms e os raios do protótipo (os tokens
de forma novos já têm uso na partida e em jogadores desde a v2-4); `--f-cond` (aponta para a Geist; o template ainda o usa, sem efeito de pixel); o canvas do replay já lê os `*-mapa` (feito na v2-4); `scripts/design/aceite.py` ainda procura `JetBrains` (v2-7).
