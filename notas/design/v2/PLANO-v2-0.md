# Plano v2-0: GOAT.demo (direção visual v2)

Só leitura. Nada foi implementado. Lido: a especificação inteira (`parser-cs2-v2.md`, 323 linhas), o protótipo (tokens, fontes, js, marca, agentes, scripts `gera_*`), e no repositório: os CLAUDE.md, `tokens.css`, `design_head.py`, `meta_da_pagina.py`, `csp.py`, `build_site.py`, `metrics/paleta.py`, `map_core.js`, `leitura/perfil_erros.py`, `pages.yml`, os testes que a v2 toca e a nota 44.
Os briefings `parser-cs2-v2.md`, `parser-cs2-briefing*.md` NÃO existem em `Claude outputs`. Só existe o prompt mestre (item 6).

## 0. Tabela rápida

| Fase | Branch | O que muda na tela | Risco |
|---|---|---|---|
| v2-1 | `v2-1-base` | Fontes Geist, tokens novos em 2 temas, CSP. Nenhuma página muda de tema ainda | Alto (mexe em muitos testes) |
| v2-2 | `v2-2-marca` | Cabra, wordmark, favicon, títulos, README | Baixo |
| v2-3 | `v2-3-landing` | Navbar nova e landing nova, com o agente | Alto |
| v2-4 | `v2-4-paginas-claras` | Partida, Jogadores e Perfil no tema claro | Alto |
| v2-5 | `v2-5-prancheta` | Prancheta em escuro violeta | Médio |
| v2-6 | `v2-6-pontos-og` | Pontos nos mapas, imagem de compartilhamento, carregamento | Médio |
| v2-7 | `v2-7-verificacao` | Nada novo: medir e capturar | Baixo |

Observação sobre a ordem: com 2 temas, v2-1 e v2-4 não podem ficar em branches com o site "meio claro, meio escuro". Por isso recomendo que o site só mude de aparência quando uma página inteira estiver pronta. Cada fase entra na main com a página dela completa (ver seção 5).

## 1. O plano em fases

Condição de merge comum a todas: suíte verde, CI verde, `py -3.12 -m scripts.design.impressao_numeros --compara` idêntico, `GRUPOS_ATIVOS = False`, nenhum e-mail do Pedro no HTML, CLAUDE.md dentro do limite. Testes existentes só mudam na lista da seção 4.

### v2-1 · Base
- Entra: `tokens.css` com dois blocos (`:root, [data-tema="claro"]` e `[data-tema="escuro"]`) mais tokens de forma. Fontes Geist e Geist Mono (woff2, 26 KB) com a OFL. Os 4 `@font-face` de fallback medidos. `design_head.py` sem Google Fonts. CSP `style-src 'self' 'unsafe-inline'` e `font-src 'self'`. Validador de paleta (`metrics/paleta.py`) por tema e para o mapa.
- Repositório: `dashboard/web/tokens.css`, `dashboard/web/fontes/*`, `scripts/design_head.py`, `scripts/csp.py`, `metrics/paleta.py`, `tests/test_csp.py` (linhas 70 e 71), `tests/test_tokens.py`, `tests/test_paleta_v2.py` e sua fixture (ver seção 4). Novo teste: fontes carregam em `file://` sem violação.
- O build copia `fontes/` para `docs/` e para `preview/`.
- Tokens que o protótipo esqueceu e o código usa: `--foco` (34 usos), `--vitoria`, `--link`, `--neutro`, `--decisivo-area`, `--tr-area`, `--sombra-pop` (7), `--peso-forte` (7), `--t-placar`, `--f-codigo` (4). Eles ficam, recalculados por tema.
- Tokens novos para o mapa (decidido, ver seção 4.3): `--tinta-2-mapa`, `--apagado-mapa`, `--fundo-mapa`, com os valores escuros de hoje.
- Condição extra: `metrics.paleta` PASSA nos temas claro, escuro e mapa. Nas capturas: nada muda para o usuário, porque as páginas ainda estão no escuro de hoje, só com a fonte nova. Se isso não for possível sem a página ficar feia, juntar v2-1 com a primeira página (ver seção 5).
- Capturas: `compara_capturas` acusa diferença nos 4 quadros por causa da fonte Geist nos nomes e no relógio do canvas. Isso é esperado. Commit próprio só com as referências novas (precedente da fase B2b).

### v2-2 · Marca
- Entra: `cabra-c.svg`, `goatdemo.svg`, `goatdemo-liso.svg`. Favicon da cabra C em `#0a0a0a` (SVG em `data:`). Títulos "… · GOAT.demo · Replay de CS2". README vira "GOAT.demo · Replay de CS2". URL e nome do repositório não mudam. Seção de terceiros do README: radares e derivados da Valve, agentes derivados de gravações do jogo, sem fins comerciais, Geist/Geist Mono sob a OFL.
- Repositório: `scripts/meta_da_pagina.py` (FAVICON e og), `scripts/build_site.py` (TITULO_DA_PAGINA), `scripts/build_web_page.py`, `README.md`, `notas/registro_tecnico_do_readme.md`, marca em `dashboard/web/marca/`.
- Testes que mudam: ver seção 4.
- Capturas: só a aba do navegador e o topo. Nada de agente, Valve ou CS2 na marca.

### v2-3 · Navbar e landing
- Entra: navbar flutuante (marca, Partidas, Jogadores, Prancheta; sem GitHub nem botão de ação). Landing nova: título pixelado (SVG), "Explorar partidas" (principal) e "Adicionar demo" (secundário, `<dialog>`, "Em breve"), três números do `numeros_citaveis`, filtros e cards, agente sorteado, laterais em pontos a partir de 1440 px, rodapé de terceiros.
- Agente: `js/agente.js` mais `agente-tr.js` e `agente-ct.js` (só o sorteado é baixado depois do `load`). Quadros fixos em SVG no HTML. TR padrão sem JS. Caixa `aspect-ratio 251/264`. `?agente=ct|tr` força o lado, para os testes e capturas.
- Repositório: `scripts/build_site.py` (a landing inteira), `scripts/design_head.py` (`topo_do_site`), CSS novo, `agente/` copiado para `docs/agente/`, `dashboard/web/agentes.manifesto.json`, `scripts/converte_agente.py` (não roda no build), teste do sha256 dos `.js`.
- Os pontos das laterais usam as máscaras de Dust II e Mirage (as duas do protótipo). A geração das máscaras no build entra aqui, e a v2-6 só estende para os outros mapas. A partida de exemplo ("Ver uma partida") deixa de ser usada no botão.
- Testes que mudam: `test_landing.py`, `test_landing_c.py`, `test_jogadores_d.py`, `test_prancheta_acabamento_browser.py`, `test_prancheta_design_e.py`, `test_acessibilidade.py`. O extrator `impressao_da_landing` precisa reconhecer os cards novos e dar as MESMAS linhas.
- Capturas: landing 375 e 1440, com `?agente=tr` e `?agente=ct`.

### v2-4 · Páginas claras (partida, jogadores, Perfil)
- Entra: `data-tema="claro"`, navbar, abas gooey (filtro só durante a troca, 220 ms), `scroll-padding-top` com `--nav-h` medido, moldura `--radar` com anel de 6 px, transporte `sticky` dentro da moldura, faixa de rounds em pílulas, Perfil com seletor em pílulas, estado vazio honesto, tipos validados. `jogadores.html` no claro.
- CSS novo NÃO vai no `template.html` (a regra do web CLAUDE.md proíbe estilo novo lá). Vai num arquivo novo `dashboard/web/v2.css`, injetado por `design_head.aplica` (um marcador novo `/*__V2__*/`).
- `map_core.js` e `annotations.js`/`tactics.js`: ler `*-mapa` (seção 4.3).
- Para o Perfil, esta fase faz SÓ a forma. A comparação nova e o mini-radar são comportamento novo (ver dúvidas 3 e 4).
- Capturas: tudo muda. Antes e depois no relatório. As 4 referências do `compara_capturas` mudam só no texto do canvas (fonte).

### v2-5 · Prancheta no escuro violeta
- `tactics.html`/`tactics.css`/`grupo.css`/`annotations.css` com `data-tema="escuro"`, "Reproduzir" com o degradê quente (uma vez por tela), `.ponto-status` com palavra, abas gooey do painel.
- Os testes de browser da prancheta (que clicam em seletores) são o risco: manter ids e classes, mudar só estilo.
- Capturas: a prancheta. O quadro `prancheta_fixture_p2` muda só na fonte.

### v2-6 · Pontos e imagem de compartilhamento
- Entra: máscaras de todos os mapas do corpus (cerca de 2 KB cada), a imagem de compartilhamento 1200×630 por partida e para a landing, e a tela de carregamento com a máscara.
- Imagem gerada com Pillow no build (ver 4.6). A og:image passa a apontar para ela.
- Capturas: `?estado=carregando` (se o Pedro aprovar, dúvida 5).

### v2-7 · Verificação final
- LCP e CLS da landing (375 px, Fast 4G, CPU 4×; limites 2,5 s e 0,1) e da partida (só CLS). Critérios A1 a A26 e N1 a N9 (seção 4.8). Capturas de todas as páginas em 375 e 1440 px. Regerar `assets/readme/*.png`. Atualizar `estado-atual.md`, PENDENCIAS (item 6 abaixo), nota 48, README, `numeros_citaveis` se preciso.

## 2. Arquivos: de onde para onde

Origem base: `TimeIA\Iriun\Sites\Base-Design\prototipos\parser-cs2-v2\` (chamo de `PROTO`). O protótipo HTML é referência: as páginas reais são os templates do projeto. Os `.html` do protótipo NÃO entram.

| Origem | Destino no repositório | Notas e peso |
|---|---|---|
| `prototipo/fontes/geist-latin.woff2` | `dashboard/web/fontes/` | 17,9 KB. Build copia para `docs/fontes/` |
| `prototipo/fontes/geist-mono-latin.woff2` | idem | 8,6 KB |
| `prototipo/fontes/OFL.txt` | idem | 4,4 KB, sem mudar |
| `prototipo/fontes/fallback.css`, `metricas-fallback.json` | NÃO entram como arquivo | O CSS dos fallbacks vai dentro de `tokens.css` |
| `gera_fontes.py` | `scripts/design/gera_fontes.py` | Entra, NÃO roda no build (precisa de `fonttools`, fora do requirements) |
| `validacao/mede_fallback.py` | `scripts/design/mede_fallback.py` | Entra, adaptado, não roda no build |
| `tokens-va.css` / `prototipo/css/tokens.css` | Vira a base de `dashboard/web/tokens.css` | Mesclar com os tokens que o código usa (v2-1) |
| `prototipo/css/base.css` (28,7 KB) | Portar para `dashboard/web/v2.css` | Não copiar cru: tem classes do protótipo |
| `prototipo/js/base.js` (6,4 KB) | `dashboard/web/v2.js` (navbar, `--nav-h`, gooey, `<dialog>`) | Injetado inline, como o resto |
| `prototipo/js/agente.js` (4,8 KB) | `dashboard/web/agente.js` | Inline na landing |
| `prototipo/agente/agente-tr.js` | `dashboard/web/agente/agente-tr.js` | 223 KB, trafega cerca de 61 KB (gzip) |
| `prototipo/agente/agente-ct.js` | `dashboard/web/agente/agente-ct.js` | 232 KB, trafega cerca de 34 KB |
| `prototipo/agente/agente-*-quadro.svg` | Dentro do HTML da landing (gerado) | 12,7 KB (TR), 15,1 KB (CT) em linha |
| `agente-pipeline/converte_agente.py` (31 KB) | `scripts/converte_agente.py` | Entra, NÃO roda no build. Importa onnxruntime, cv2, rembg: não pode ser importado por teste nenhum |
| `agente-pipeline/variacoes.py`, `profundidade.py`, `analisa_fonte.py`, `gera_folhas_rodada_final.py` | NÃO entram | Histórico. A profundidade foi descartada |
| (novo) manifesto | `dashboard/web/agentes.manifesto.json` | sha256 de vídeos, modelos e dos 2 `.js` (valores na especificação §6.4) |
| `fonte-agente/` (vídeos, quadros com cartão de jogador) | NÃO entra | Material bruto |
| `agentes/` (TRV1 e rodada-final) | NÃO entra | TRV1 é reserva congelada, fora do repo |
| `capturas/` | NÃO entra | Só referência |
| `prototipo/marca/cabra-c.svg`, `goatdemo.svg`, `goatdemo-liso.svg` | `dashboard/web/marca/` | Cerca de 3,5 KB. Não levar `cabra-a`, `cabra-b`, `wordmark-1..3` |
| `gera_marca.py` | `scripts/design/gera_marca.py` | Entra, não roda no build |
| `gera_pontos.py` | `scripts/design/gera_pontos.py` | Roda no build, mas lendo o radar do `.json` (ver 4.5). 1,9 a 2,1 KB por mapa |
| `gera_og.py` | Reescrever em Pillow: `scripts/design/gera_og.py` | O original usa Playwright com `channel="chrome"` e não roda no CI de build (ver 4.6). Imagem 70 a 95 KB por PNG |
| `prototipo/img/og-*.png` | NÃO entram | São exemplo |
| `prototipo/img/radar-mirage.webp` | NÃO entra | Arte da Valve em exemplo |
| `gera_prototipo.py`, `gera_esbocos.py`, `gera_indice.py`, `gera_prancha.py`, `pontos.html`, `marca.html`, `variacao-*.html`, `tokens-vb.css`, `agente.html`, `agente.js` (da pasta pai) | NÃO entram | Só do protótipo |
| `validacao/aceite_fase2.py`, `mede_fase2.py`, `mede_modos.py` | Adaptar para `scripts/design/aceite_v2.py` | Usado na v2-7. Os existentes (`aceite.py`, `mede_lcp_cls.py`) têm de ser atualizados também |
| `validacao/paleta_v3.py` | NÃO entra | Vira a extensão de `metrics/paleta.py` |
| `projetos/parser-cs2-v2.md` | `notas/design/entrega-v2-goatdemo.md` | Cópia, como foi feito com a Sala de demo |
| (novo) | `notas/decisoes/48-direcao-visual-goatdemo.md` | Ver 4.9 |

Efeito no peso:
- Páginas de partida (2,1 a 2,6 MB cada): +26 KB de fonte, baixados uma vez e reaproveitados. Menos o pedido ao Google Fonts. HTML cresce cerca de 30 KB (CSS e JS novos), cerca de 5 KB comprimido.
- Landing: o HTML hoje tem 58 KB (10,7 KB comprimido). Soma cerca de 25 KB de CSS e SVGs. O agente baixa 34 ou 61 KB (gzip) depois do `load`. Sem a imagem `replay.webp` (27 KB) na página. Total do primeiro carregamento cerca de 70 KB (CT) a 100 KB (TR) comprimidos. Medido no protótipo: LCP 0,68 a 0,92 s, CLS 0 a 375 px (0,0065 a 1440 px).
- `docs/`: cerca de +4 MB por causa das 52 imagens de compartilhamento (cerca de 70 KB cada). Hoje `docs/` tem 174 MB.
- Repositório: +26 KB de fontes, +455 KB dos dois agentes, +40 KB de scripts. Não entra vídeo.

## 3. Dúvidas que são escolha do Pedro

Cada uma com opções e a minha recomendação. As decisões técnicas eu já tomei (seção 4).

1. **O que acontece com o GitHub no site.** A navbar nova não tem link do GitHub, e o "Código no GitHub" da landing some junto com o `replay.webp`.
   - A) Só um link discreto no rodapé da landing. B) No rodapé de todas as páginas. C) Só dentro do diálogo "Adicionar demo" (issue).
   - Recomendo A mais C: o portfólio precisa mostrar o código, e o diálogo precisa do link da issue de qualquer jeito.
2. **O botão principal da landing.** A especificação manda "Explorar partidas" levando à lista. Hoje "Ver uma partida" abre uma partida escolhida por critério declarado (profissional, decisiva, placar apertado).
   - A) Seguir a especificação, e a partida de exemplo vira o primeiro card em destaque. B) Manter o atalho para a partida de exemplo como link secundário.
   - Recomendo A. Fica o mesmo critério de escolha, só usado para ordenar. Se o Pedro quiser B, é um botão a mais.
3. **A "Comparação lado a lado" do Perfil (especificação §5.4).** Não existe hoje. Hoje o "Comparar com" mostra os mesmos tipos e pontos fortes de dois jogadores. A nova tem grupos (Impacto, Abertura, Trocas, Utilidade, Situações) e uma frase "quem está melhor escrito" ("kairo à frente", "empate na prática", "amostra pequena"). Isso é critério de jogo novo: precisa de uma regra de "empate na prática".
   - A) Só a forma nova sobre o comportamento de hoje (agora). B) Fazer a comparação nova numa fase própria depois da v2, com a regra de empate definida por você, citando bruto e referência. C) Fazer agora com uma regra minha.
   - Recomendo A agora e B depois. A v2 "muda só a forma", e a frase "à frente" afirma algo de jogo sem você ter validado.
4. **O mini-radar do Perfil** (abates e mortes como pontos no mapa, cada ponto leva ao Replay). É recurso novo, com dado novo (posições, agrupamento acima de 30 pontos). O nome "mini-radar" também bate com a regra "nada de gráfico de radar".
   - A) Fora da v2. B) Dentro, em fase própria. C) Dentro, na v2-4.
   - Recomendo A, e se for feito um dia, chamar de "mini-mapa". As posições das mortes já existem em outras telas, então não é impossível, só não é forma.
5. **A tela de carregamento com "progresso real".** O dado da partida já vem embutido no HTML. A nota 44/§19 diz que "Carregando" não existe no site real. Não há progresso para medir.
   - A) Não fazer a tela. B) Fazer um esqueleto com a máscara do mapa, sem porcentagem, enquanto o JS monta o Replay. C) Fazer com porcentagem inventada (não recomendo, seria número falso).
   - Recomendo B (também serve de esqueleto contra CLS, como a §19.8 já pede).
6. **Código e comandos de console em fonte do sistema.** A especificação diz "nome de arquivo ou código em sans com fundo, nunca mono". Hoje os comandos `setpos`/`setang` usam `--f-codigo` (mono do sistema), e `test_tokens` exige esse token.
   - A) Seguir a especificação (sans). B) Manter a mono do sistema só para comando que se copia.
   - Recomendo B. Em sans, `0`/`O` e `l`/`1` se confundem num comando que o jogador cola no console. A mono do sistema não é fonte baixada, então não conta nas 2 famílias.
7. **Imagem de compartilhamento: por partida ou por mapa.** 52 imagens (cerca de 3,6 MB, placar no texto) ou 8 (uma por mapa, sem placar).
   - Recomendo por partida: o placar é o que faz alguém clicar. O custo é pequeno.
8. **Texto do estado vazio do Perfil.** A especificação troca "Em validação: os tipos de erro aparecem depois de conferidos" por "Ainda estamos conferindo estas leituras com partidas reais. Elas aparecem aqui quando estiverem validadas." mais o link "Como é conferido".
   - Recomendo aceitar o texto da especificação (você já aprovou o design), e conferir se "partidas reais" é verdade: os exemplos vêm do corpus de demos reais, então sim.
9. **Texto da nota "Em breve" e do diálogo "Adicionar demo".** O diálogo diz "as partidas são processadas no computador do autor". Isso é um texto de site novo.
   - Recomendo aceitar, com o link da issue sem e-mail.
10. **O agente sorteado e o nome na marca.** "Nada da Valve na marca" e o agente é derivado de gravação do jogo. Já aprovado por você (N8). Só confirmar que o agente pode aparecer na landing com a linha de terceiros do rodapé (a especificação já escreve a linha).
    - Recomendo manter. Só confirmo porque é o ponto mais sensível do ponto de vista de licença.

## 4. Conflitos com as regras do projeto, e como resolver

### 4.1 CSP, `font-src` e `file://`
- `scripts/csp.py` tem `font-src https://fonts.gstatic.com` e `style-src … https://fonts.googleapis.com`. `tests/test_csp.py` linhas 70 e 71 afirmam isso. O Pedro autorizou a mudança só dessas duas linhas. Mudo exatamente isso, nada mais no arquivo (docstring do teste e `csp.py` falam do Google Fonts; a docstring do `csp.py` não é teste).
- Risco real: CSP com `'self'` quando a página abre como `file://`. O protótipo mediu "Geist: loaded" com `font-src 'self'`, mas em Chrome. Resolvo com um teste NOVO (não altera os existentes) que abre landing, partida e prancheta em `file://`, com a pasta `fontes/` ao lado, e confere `document.fonts` Geist e Geist Mono em `loaded`, zero violações, e o `agente-tr.js` carregando. O `<script src>` dinâmico do agente em `file://` com `script-src 'self'` NÃO foi medido na especificação (só em HTTP e no protótipo sem o teste de violação). Se Chrome bloquear, o plano B é `script-src 'self' 'unsafe-inline'` já cobrir (o protótipo usa o mesmo). Será medido na v2-1.
- Autocontida: a página continua abrindo da pasta `docs/` sem rede (melhor que hoje, que precisa do Google). Um HTML solto copiado para outro lugar perde fontes e agente, e cai no fallback medido e no quadro fixo. Deixo escrito na nota 48.

### 4.2 Limite de 2 famílias
- Geist e Geist Mono contam como as 2. Os apelidos `Geist Fallback`/`Geist Mono Fallback` são `local()` e não baixam nada (mesma lógica da §15 A6). `aceite.py` menciona `JetBrains` e precisa ser atualizado para o nome novo.
- `--f-codigo` (mono do sistema) não é fonte baixada. Ver dúvida 6.
- O texto do canvas: `map_core.js` linha 297 usa `'DM Sans'` (resto de uma fase antiga) e as outras linhas usam `token("f-num")`/`token("f-texto")`, então a fonte nova entra pelos tokens. A linha 297 não é afetada, mas é um sobra que o A6 deve checar.

### 4.3 O mapa e o tema claro (conflito mais sério de código)
A especificação diz que `map_core.js` muda "só a fonte e as cores lidas de `--*-mapa`". Mas `map_core.js`, `tactics.js` e `annotations.js` leem, por `token()`, as cores `tinta` (21 usos), `tinta-2`, `apagado` (cor da isca), `foco` e `fundo`. No tema claro `--tinta` é `#0a0a0a` sobre o radar `#0f141b`: contraste 1,07:1. Rótulos, relógio e a granada isca sumiriam. E `apagado` claro dá 3,47:1 sobre o radar.
- Resolução: trocar `token("tinta")` por `tinta-mapa`, `foco` por `foco-mapa`, e criar `tinta-2-mapa`, `apagado-mapa` e `fundo-mapa` com os valores escuros de hoje (`#aab5c1`, `#8b97a5`, `#0b0f14`), todos validados contra `--radar`. O validador cobre o grupo "mapa".
- O teste `test_as_cores_das_granadas_do_canvas_vem_dos_tokens` espera `decoy == tk["apagado"]` e o de pixel espera `tk["tr"]`: viram `apagado-mapa` e `tr-mapa` (autorização do Pedro necessária, seção 4.4).
- `NADE_COLOR` é lido na carga, antes de qualquer troca de tema: como o tema é fixo por página, está certo.
- A13, A14 e A25 (radar, anel duplo, granada) não mudam de cor. Mudam os pixels do TEXTO do canvas (fonte). Por isso A11 (`mede_texto_mapa.py`) precisa ser refeito. A especificação não lista A11.

### 4.4 Testes existentes que quebram e precisam da autorização do Pedro
A regra da raiz é "teste existente não muda sem o Pedro aprovar". O Pedro autorizou só `test_csp.py` linhas 70 e 71. A lista abaixo é o que a v2 quebra de verdade. Peço a autorização de todos na entrega deste plano:

| Teste | Por que quebra | Mudança |
|---|---|---|
| `test_tokens.py::test_tokens_css_tem_os_mesmos_valores_do_prototipo_do_design` | Compara com `notas/design/prototipo/tokens.css` (Sala de demo) e exige que só `--f-codigo` seja extra | Passar a comparar com o protótipo v2, ou comparar por tema |
| `test_tokens.py::test_paginas_geradas_nao_deixam_marcador…` | `FONTES_URL`, `--fundo: #0b0f14`, `Archivo Fallback`, "2 famílias no URL do Google" | Reescrever para Geist (sem URL externa) |
| `test_tokens.py::test_toda_pagina_recebe_os_tokens_e_as_fontes_pelos_marcadores` | Exige `<!--__FONTES__-->` (1 por página) | Manter o marcador (decisão técnica: ele passa a injetar o CSS das fontes), e este teste pode ficar intacto |
| `test_tokens.py::test_o_favicon_tem_as_duas_bolinhas…` | Favicon vira a cabra C | Reescrever |
| `test_tokens.py::test_as_cores_das_granadas…` e `…a_peca_da_prancheta…` | Ver 4.3 | Trocar para `*-mapa` |
| `test_paleta_v2.py` e `tests/fixtures/paleta_v2_saida.txt` | Saída fixa de 23 tokens num tema só; `le_tokens` lê o último valor de cada nome | Fixture nova por tema; manter o teste antigo como "tema escuro violeta/ mapa"? Não: é outra saída. Reescrever |
| `test_landing.py` | Exige exatamente `btn-partida`, `btn-prancheta`, `btn-github` | Reescrever (ids e links novos) |
| `test_landing_c.py` | `TITULO_DO_TOPO`, `<img … lazy>`, `figcaption` do replay, `btn-partida` na dobra | Reescrever |
| `test_cabecalho.py` (linha 118) e `test_textos.py` (linha 58) | `<title>` termina em " · Parser de Replay CS2" | Terminar em " · GOAT.demo · Replay de CS2" |
| `test_acessibilidade.py` (linha 66) | `og:image` = `replay.png` | Apontar para a imagem nova |
| `test_jogadores_d.py` (linha 47), `test_prancheta_acabamento_browser.py` (linha 15) e `test_prancheta_design_e.py` | `<header class="site-topo">`, `.site-topo .marca` | Mantenho essas classes na navbar nova se for possível (decisão técnica), e então estes ficam intactos. Se não, mudo só o seletor |
| `tests/test_numeros_citaveis.py` | Não quebra | |

Regra para mim: antes de mudar qualquer teste, tento manter ids e classes para NÃO mudar o teste. Só mudo o teste quando o comportamento visível muda por decisão do design.

### 4.5 Radar na hora do build
`assets/radars/*.png` está no `.gitignore`. No CI só existe o `.json`, com a imagem em base64 dentro. A especificação diz que o `gera_pontos.py` lê "o radar que já está no projeto". Resolução: o gerador decodifica a imagem do `.json`. Gera só os mapas que têm partida no corpus (8) mais os usados em OG. Determinístico (Pillow).

### 4.6 Imagem de compartilhamento no CI
O `gera_og.py` do protótipo usa Playwright e `channel="chrome"`. O job `build` do `pages.yml` instala só `requirements.txt` (sem Playwright nem Chromium). Opções: pôr Chromium no job de build; ou gerar com Pillow. Decido: Pillow. Texto com o TTF estático do Geist (instância de 600 e 400, e Mono 500, gerada uma vez pelo `gera_fontes.py` a partir do pacote OFL, 100 a 150 KB cada no repositório, em `scripts/design/fontes_og/`). A marca (cabra e wordmark) é um PNG pré-renderizado e versionado, já que as letras são polilinhas de SVG. Fica determinístico, sem navegador no build.

### 4.7 `tests/CLAUDE.md`, `dashboard/web/CLAUDE.md` e a raiz
- `dashboard/web/CLAUDE.md` tem 5.095 bytes (limite 6.000). Tenho de trocar duas linhas (CDN e 2 famílias; "página da partida sem o topo", que a v2 inverte) e acrescentar 2 ou 3 (temas, `*-mapa`, `v2.css`). Estimo +450 bytes: cabe em cerca de 5.550.
- `scripts/CLAUDE.md` está em 5.969 bytes de 6.000. Qualquer regra de build nova (pontos, OG, fontes) NÃO cabe. Vai para a nota 48 e para o CLAUDE.md do `dashboard/web/`. Se precisar mesmo, paro e trago uma proposta de divisão (regra do `estado-atual.md`).
- Raiz: 10.508 bytes (limite do teste 15.000). Mudanças: o índice aponta também para `entrega-v2-goatdemo.md`.
- Decisão 44: continua vigente para cor, mapa e "uma cor, um papel". A parte de tema único, Archivo/JetBrains, Google Fonts e "partida sem topo" é revista. O teste `test_claude_md` obriga que decisão vigente seja citada e que superada NÃO seja. Resolução: nova nota 48 (vigente), 44 permanece vigente com um aviso "revista pela 48 em X", e os CLAUDE.md citam (48) nas linhas que mudam. Assim os dois ficam citados.

### 4.8 Critérios A1 a A26, recalculados
A especificação só lista A1-A9, A12-A14, A25, A26 e N1-N9. Faltam A10, A11, A15-A24 (da §15 e §19.11 antigas). Faço assim em dois temas (claro nas páginas, escuro na prancheta, mapa sempre escuro):

| Critério | v2 |
|---|---|
| A1 transporte visível | Refazer: transporte `sticky` dentro da moldura, com a navbar de 76 px no topo |
| A2 sem rolagem horizontal | Refazer em todas as páginas, 375/768/1440 |
| A3 contraste de texto, A4 marcas | Refazer nos 2 temas (`aceite.py` precisa ler `data-tema`) |
| A5 toque 44 px | Refazer; pílulas e chips novos |
| A6 e A24 duas famílias | Atualizar nomes para Geist; o código do grupo continua exceção |
| A7 "Time A/B" | Igual |
| A8 paleta | Três saídas: claro, escuro, mapa |
| A9 abas por teclado | Refazer com o gooey |
| A10 prancheta | Refazer (cliques, relógio, Home, Reproduzir) |
| A11 texto no mapa | Refazer (fonte mudou) |
| A12 LCP/CLS | Landing e partida |
| A13, A14, A25 | Cor igual; refazer só se uma cor do canvas mudar (aceito pelo Pedro). Eu recomendo rodar `mede_radar`/`mede_granada_real` mesmo assim, já que a fonte e a escala da moldura mudaram o tamanho do canvas |
| A15 mapa sem entrada | Igual |
| A16 a A23 (Perfil, Grupo) | Refazer; A20 (erro de jogador sem `--erro`/`--aviso`) em especial, porque a v2 mexe nos cards |
| A26 CLS partida e prancheta | Refazer |
| N1 a N9 | N2 (só o agente sorteado baixa) e N6 (sem JS) viram teste de browser com `?agente=` |

Medir a landing com `?agente=ct` e `?agente=tr` (o sorteio é aleatório e ficaria instável).

### 4.9 `compara_capturas` e as referências
Os 4 quadros recortam só o canvas (`#map` e `#pr-mapa`). Se a v2 só trocar a fonte do texto, os pixels mudam apenas nos rótulos e no relógio. Isso vai acusar diferença, é esperado e autorizado pela especificação ("o mapa não muda"). Regeração das referências em `notas/design/referencias/design-v2/`, em commit próprio, com a lista dos pixels fora da vizinhança de um jogador (o critério do script). Se uma peça ou o fundo mudar de pixel, é bug.

### 4.10 `impressao_numeros`
A impressão cobre os blobs de dado e os cards da landing por regex de classe (`mcard`, `mscore`, `cp-linha`…). Se eu mudar as classes dos cards, o extrator tem de ser atualizado e produzir as MESMAS linhas. Faço isso com uma comparação dos dois extratores no commit. O extrator vive em `scripts/design/` (não é teste), então é uma mudança de ferramenta, não de teste.

### 4.11 README, `numeros_citaveis` e o e-mail
- README: título, seção de terceiros, imagens `assets/readme/*.png` (feitas no design antigo; regerar na v2-7 com `capturas_readme.py`, que também usa "Ver uma partida" e vai quebrar até ser adaptado).
- Os três números da landing continuam vindo do `numeros_citaveis.json`. Nenhum número escrito no template. O README já tem testes de sincronia.
- E-mail: o diálogo e o rodapé usam só o link de Issues. Teste novo: nenhum `@` com cara de e-mail nas páginas.

### 4.12 O CLAUDE.md "Nenhum texto nem estilo novo no template.html"
A v2 precisa de muito CSS novo. Resolução: arquivo `dashboard/web/v2.css`, injetado pelo `design_head.aplica`, e `template.html` ganha só o marcador e a estrutura (a navbar, o `<dialog>`). Os textos (navbar, diálogo, rodapé) saem de Python (`PAGINA.landing.textos`), como a decisão 18 manda.

## 5. Riscos e ordem

Ordem recomendada: v2-1, v2-2, v2-3, v2-4, v2-5, v2-6, v2-7.

- **v2-1 e v2-2 podem ir em paralelo?** Não de verdade: v2-2 mexe em `meta_da_pagina.py` e em testes de título e favicon, que v2-1 já mexe. Faça v2-1 primeiro. v2-2 é pequena, vale fazer em seguida, no mesmo dia.
- **v2-3 e v2-4 não vão em paralelo.** Ambas criam a navbar e o `v2.css`. Faça a navbar na v2-3 e a v2-4 consome.
- **v2-5 pode ir em paralelo com v2-4** em worktrees separados, porque mexem em arquivos diferentes (`tactics.*`, `grupo.css`, `annotations.css` contra `template.html`). Mas `annotations.css`/`map_core.js` são compartilhados com a v2-4. Só vale em paralelo depois de a v2-4 ter feito a mudança do `map_core.js` e mesclado.
- **v2-6 depende da v2-3** (as máscaras das laterais) e da escolha da dúvida 5. Pode ir em paralelo com a v2-5.
- **v2-7 por último.**

Riscos principais:
1. Testes que quebram em lote na v2-1 (seção 4.4). Mitigação: pedir a autorização da lista agora.
2. Site "meio claro, meio escuro" se a v2-1 for mesclada sem a v2-3/v2-4. Mitigação: a v2-1 não muda a aparência (só a fonte e os tokens do tema escuro atual sob o nome `data-tema="escuro"`), e só no merge da v2-3 e v2-4 a landing e a partida viram claras. Dá para a v2-3 e a v2-4 irem juntas ao `main` no mesmo push (CLAUDE.md: "push só no fim" foi a regra da Sala de demo).
3. Mapa ilegível no tema claro (4.3). Mitigação: tokens `*-mapa` e A11 refeito.
4. LCP da landing com o agente. Medido no protótipo (0,68 a 0,92 s), mas sem o dado real. Refazer na v2-7.
5. O `Content-Encoding` do `.js` do agente: o GitHub Pages só serve gzip; só se confirma depois do primeiro deploy.
6. CSP com `file://` (4.1).
7. `scripts/CLAUDE.md` sem folga (4.7).

PENDENCIAS_PARA_O_PEDRO (a anotar na v2-7): (a) depois do primeiro deploy, `curl -sI -H "Accept-Encoding: gzip, br" <url>/agente/agente-tr.js` e `agente-ct.js`; (b) fallback da fonte mono no macOS (cai em Menlo, sem métrica medida); (c) se o Pedro escolher A na dúvida 3/4, o cartão da comparação nova e do mini-mapa.

## 6. Inconsistências da especificação

1. §6.4 diz que os `.js` dos agentes ficam em `dashboard/web/`; §10 diz "copiar `agente/` para `docs/`". Resolvo: `dashboard/web/agente/` no repo, `docs/agente/` no site.
2. Tamanhos: a especificação diz `agente-tr.js` 223.263 B e `agente-ct.js` 232.444 B; os arquivos do protótipo têm 223.271 e 232.452. O sha256 bate (857fb00c… e a71af4e0…), então a diferença é só de contagem. O teste do manifesto usa o sha256.
3. A tabela §6.3 ainda mostra o CT-A antigo (236.364 B); o final está na caixa "AGENTES APROVADOS". A §6.2 tem comentário "sem sorteio enquanto nenhum CT estiver aprovado" (já superado). O N6 diz "quadro fixo do CT" na coluna da pergunta e "TR" na resposta.
4. Tokens: a §2.2 não lista `--foco`, `--vitoria`, `--link`, `--neutro`, `--*-area`, `--sombra-*`, `--peso-*`, `--t-placar`, `--f-codigo`, que o código usa. O protótipo tem `--foco` e os outros somem. Tenho de recalcular (v2-1).
5. §10 diz que `map_core.js` muda "só a fonte e as cores `*-mapa`", mas faltam `tinta-2`, `apagado` e `fundo` do mapa (4.3).
6. A lista de critérios da §12 só tem uma parte dos A (faltam A10, A11, A15-A24).
7. §5.4 inclui mini-radar e comparação por grupos com "quem está melhor": comportamento novo, que contradiz "A v2 é forma" (§0 e §11).
8. §5.3 "Carregando… 62%" pelo progresso real não tem fonte de dado no site real.
9. §3.4 manda código em sans; a regra do projeto e o teste mantêm `--f-codigo`.
10. §5.1 diz que a navbar não tem botão de ação nem GitHub. Hoje o GitHub está no topo e na landing; a especificação não diz onde fica.
11. §9: gera_pontos "no build" e gera_og "no build" não dizem como rodam no CI (PNG do radar ausente, Playwright ausente).
12. §3.1 diz que não há `preload` com `crossorigin` porque `file://` bloqueia. Sem preload, o LCP pode piorar em HTTP real; foi medido só com o servidor local do protótipo. Refazer na v2-7 no Pages.
13. §5.2 item 4 usa "100% da largura útil"; o texto da mesma linha dá 104 px a 1440, ou seja, o mapa lateral mede 104 px de largura. Pequeno, mas a "forma" do mapa em pontos a 1440 pode ler mal. A decisão foi do Pedro (Fase 2b), só aviso.
14. `AGENTES APROVADOS` diz que sem JS aparece o TR "aprovado primeiro e lê melhor"; a regra de privacidade diz que o CT-A usa corte `y<545`, e o TR `y<590`. Não há contradição, mas a §6.1 (`590` para os dois) está desatualizada.

## 7. O que não fiz / não conferi
- Não abri as páginas no navegador nem rodei a suíte (só leitura).
- Não conferi o texto completo de `css/base.css`, `partida.html` e `estados.html` do protótipo, só a estrutura e o que a especificação cita.
- Não medi se `script-src 'self'` carrega o `agente-*.js` em `file://` (4.1).
- Não li a `entrega-sala-de-demo.md` §7 a §11 inteiras nem as notas 30, 41 e 46 por completo.
