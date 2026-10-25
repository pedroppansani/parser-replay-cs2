# Parser de Replay CS2 · direção v2 "GOAT.demo" · documento de entrega para implementação

> **Para quem:** a sessão do projeto (Code), implementar sem perguntar. **Data:** 2026-10-15/16 (Fase 2 da v2), revisado na Fase 2b (2026-10-16): navbar final, botões invertidos, cards de mapa, confirmações do Pedro e agentes em escolha.
> **Decisões do Pedro:** `projetos/parser-cs2.md` §19.13 (não repetidas aqui; esta especificação as cumpre).
> **Protótipo navegável** (abre como arquivo local): `prototipos/parser-cs2-v2/prototipo/` — `indice.html` (índice do protótipo, a única entrada para as páginas de apoio), `index.html` (landing), `partida.html` (6 abas, `#resumo` … `#estilos`; `?estado=carregando`), `prancheta.html`, `jogadores.html`, `marca.html`, `estados.html` (catálogo), `agente.html` (prova do agente).
> **Medições:** `prototipos/parser-cs2-v2/validacao/` (`saida-fase2-a-claro.txt`, `saida-fase2-a-escuro.txt`, `saida-fase2-a-mapa.txt`, `saida-fallback.txt`, `saida-aceite-fase2.txt`, `saida-medidas-fase2.txt`) e `capturas/`.
> **A v2 é forma.** Comportamento de replay, prancheta, grupos, Perfil e os testes existentes não mudam (exceto o `test_csp.py`, §3.3, que precisa do OK do Pedro).

---

## 1. Marca

| Peça | Arquivo | Regra |
|---|---|---|
| Cabra C (selo hexagonal) | `prototipos/parser-cs2-v2/marca/cabra-c.svg` (viewBox 64, `currentColor`) | favicon, avatar padrão, símbolo ao lado do wordmark. Nada de corpo, pernas ou perfil (R2/Bencho). |
| Wordmark GOAT.demo com mira | `marca/goatdemo.svg` | só de **24 px de altura para cima**: o "O" de GOAT tem a mira (4 ticks, traço 0,55); o "o" de ".demo" nunca. |
| Wordmark liso | `marca/goatdemo-liso.svg` | abaixo de 24 px (cabeçalho a 17 px, aba). |
| Gerador | `gera_marca.py` | as letras são polilinhas; nenhuma fonte de marca é carregada. |

- Em texto: sempre **"GOAT.demo · Replay de CS2"** (`<title>`, `og:title`, README); nunca "GOAT" sozinho.
- Favicon: a cabra C em `#0a0a0a`, SVG em `data:` (o CSP já permite `img-src data:`).
- **Nunca na marca:** agente, logo/ícone/nome estilizado da Valve ou do CS2. Nome do mapa em texto pode.
- A e B (`cabra-a.svg`, `cabra-b.svg`) ficam só como histórico nos protótipos.

## 2. Tokens nos dois temas

**Fonte única:** `prototipos/parser-cs2-v2/tokens-va.css` (cópia em `prototipo/css/tokens.css`). Um `--token: #hex;` por linha (o validador lê). Tema por página: `<html data-tema="claro">` (landing, todas as abas da partida, `jogadores.html`) e `data-tema="escuro"` (prancheta). **O canvas do mapa é sempre escuro** (`--radar`) e usa só os tokens `*-mapa`, iguais nos dois temas.

### 2.1 Valores e contraste medido (saída de `validacao/paleta_v3.py`, RESULTADO: PASSA nos três)

| Token | Claro | pior contraste (fundo) | Escuro violeta | pior contraste | Papel |
|---|---|---|---|---|---|
| `--fundo` | `#ffffff` | — | `#04061c` | — | página |
| `--superficie` | `#fafafa` | — | `#0c0a2b` | — | card, painel, navbar |
| `--superficie-2` | `#f5f5f5` | — | `#15153d` | — | elevado, hover, pílula das abas |
| `--tl-fundo` | `#fafafa` | — | `#080a24` | — | linha do tempo |
| `--radar` | `#0f141b` | — | `#0f141b` | — | canvas do mapa (sempre escuro) |
| `--tinta` | `#0a0a0a` | 18,16 | `#ffffff` | 17,41 | texto, vitória, link, foco |
| `--tinta-2` | `#525252` | 7,17 | `#b4b4bb` | 8,44 | secundário |
| `--apagado` | `#6b6b6b` | 4,89 | `#9b9ba4` | 6,31 | rótulo, neutro |
| `--linha` | `#e5e5e5` | decorativa | `#292a4d` | decorativa | divisória |
| `--borda` | `#858585` | 3,38 | `#6a6ca0` | 3,54 | borda de controle (marca) |
| `--ct` / `--ct-texto` | `#2a78d6` / `#1f62c4` | 4,05 / 5,35 | `#4a90e8` / `#6ea8f2` | 5,34 / 7,08 | lado CT |
| `--tr` / `--tr-texto` | `#d9662a` / `#822810` | 3,27 / 8,52 | `#e0a23a` / `#e9b65a` | 7,79 / 9,37 | lado TR |
| `--decisivo` | `#0b6b4a` | 5,99 | `#2fae7c` | 6,19 | afirmado e bom |
| `--aviso` | `#9c6004` | 4,71 | `#ffea3d` | 14,16 | algo a refazer, sempre com ▲ |
| `--erro` | `#b81c42` | 5,87 | `#ff6b6b` | 6,27 | falha de sistema, sempre com ✕ e "Erro:" |
| `--acao` / `--acao-ink` | `#0a0a0a` / `#ffffff` | 19,80 | `#ffffff` / `#04061c` | 20,04 | botão principal, aba ativa |
| `--quente-1` → `--quente-2` | — | — | `#ffb4a0` → `#ff3a63` | 5,00 | **só** o "Reproduzir" da prancheta, uma vez por tela; texto `--quente-ink #04061c` (5,76) |
| mapa: `--ct-mapa` `#4a90e8`, `--tr-mapa` `#e0a23a`, `--smoke` `#d1d9e0`, `--flash` `#f9f5b8`, `--he` `#ff4da6`, `--molotov` `#d65d00`, `--aviso-mapa` `#ffea3d`, `--tinta-mapa`/`--foco-mapa` `#ffffff`, `--contorno` `#05080b` | — | contra `--radar`: 4,77 (molotov) a 18,48 | iguais | iguais | peças, granadas, rótulos no mapa |

Daltonismo (ΔE2000, pior de protanopia e deuteranopia, ≥ 8): dados no claro 13,6; estados em texto no claro 10,0 (aviso × erro); mapa 12,3 (TR × molotov); coral `#ffb4a0` × decisivo 8,1 (o coral original `#ff8a76` dava 2,7: `saida-coral-original.txt`).

### 2.2 Tabela "token atual → token novo" (projeto `dashboard/web/tokens.css`, lido em 2026-10-15)

O arquivo continua sendo a fonte única e injetado como hoje (`/*__TOKENS__*/`); ganha **dois blocos** (`:root, [data-tema="claro"]` e `[data-tema="escuro"]`). O `metrics/paleta.py` passa a validar os dois blocos (mesmas regras do `paleta_v3.py`).

| Atual (Sala de demo, escuro único) | Novo claro | Novo escuro (prancheta) | Observação |
|---|---|---|---|
| `--fundo #0b0f14` | `#ffffff` | `#04061c` | |
| `--superficie #121820` | `#fafafa` | `#0c0a2b` | |
| `--superficie-2 #1a222d` | `#f5f5f5` | `#15153d` | |
| `--radar #0f141b` | igual | igual | o mapa não muda: §4.1 do `parser-cs2.md` (RADAR_AJUSTE, anel duplo) vale sem alteração |
| `--tl-fundo #0e131a` | `#fafafa` | `#080a24` | |
| `--tinta #e8edf2` | `#0a0a0a` | `#ffffff` | |
| `--tinta-2 #aab5c1` | `#525252` | `#b4b4bb` | |
| `--apagado #8b97a5` | `#6b6b6b` | `#9b9ba4` | |
| `--linha #222b37` | `#e5e5e5` | `#292a4d` | |
| `--borda #66758a` | `#858585` | `#6a6ca0` | |
| `--ct #4a90e8` · `--ct-texto #6ea8f2` | `#2a78d6` · `#1f62c4` | iguais aos atuais | |
| `--tr #e0a23a` · `--tr-texto #e9b65a` | `#d9662a` · `#822810` | iguais aos atuais | |
| `--decisivo #2fae7c` | `#0b6b4a` | igual | |
| `--aviso #ffea3d` · `--erro #ff6b6b` | `#9c6004` · `#b81c42` | iguais | |
| `--smoke`, `--flash`, `--he`, `--molotov` | renomear para uso no canvas; valores iguais | iguais | `NADE_COLOR` do `map_core.js` lê `--smoke/--flash/--he/--molotov` (sem mudança de valor) |
| (novo) | `--ct-mapa`, `--tr-mapa`, `--aviso-mapa`, `--tinta-mapa`, `--foco-mapa` | iguais | o canvas lê estes, não os do tema (no claro `--ct` é mais escuro e sumiria no radar) |
| (novo) | `--acao #0a0a0a`, `--acao-ink #fff` | `#fff` / `#04061c` | botão principal e aba ativa |
| (novo) | — | `--quente-1 #ffb4a0`, `--quente-2 #ff3a63`, `--quente-ink #04061c` | só "Reproduzir" |
| `--f-texto` Archivo · `--f-cond` · `--f-num` JetBrains Mono | `--f-texto: "Geist", "Geist Fallback", …` · `--f-num: "Geist Mono", "Geist Mono Fallback", …` | iguais | `--f-cond` sai (sem condensada na v2) |
| `--r-sm 3px`, `--r-md 4px` | `--r-card 16px`, `--r-ctl 999px`, `--r-cab 999px`, `--r-moldura 20px`, `--r-mapa 12px` | iguais | §4 |
| `--dur 120ms` | `--dur 220ms`, `--curva cubic-bezier(.3,1.25,.5,1)` | igual | 0 ms com reduzir movimento |
| (novo) | `--nav-h` (medido pelo JS) | igual | §8 (C2) |

## 3. Tipografia (C3)

### 3.1 Fontes hospedadas no próprio site
- **Geist** (variável, eixo `wght` limitado a 400–600) e **Geist Mono** (400–600), do pacote npm oficial `geist` 1.7.2 (Vercel, `github.com/vercel/geist-font`), **SIL OFL 1.1**.
- Subconjunto latino em woff2, gerado por `prototipos/parser-cs2-v2/gera_fontes.py`: `geist-latin.woff2` **17.852 bytes**, `geist-mono-latin.woff2` **8.560 bytes** (mono só com ASCII e sinais: é só número). **Total: 26.412 bytes.**
- A licença vai junto: `fontes/OFL.txt` (cópia sem mudança). README, seção de terceiros: "Fontes Geist e Geist Mono (Vercel), SIL Open Font License 1.1".
- Arquivos ao lado da página (`docs/fontes/`), `@font-face` com `url(fontes/…)` e `font-display: swap`. **Sem `<link rel=preload … crossorigin>`**: em `file://` o preload com `crossorigin` é bloqueado por CORS (medido); sem ele, o Chrome carrega as fontes de `file://` (medido: `Geist: loaded`).
- Nenhum pedido ao Google Fonts. No máximo 2 famílias (A6: `Geist`, `Geist Mono` + os apelidos locais `… Fallback`, que não baixam nada).

### 3.2 Fallbacks medidos (não estimados) — `validacao/mede_fallback.py`, Chrome no Windows
```css
@font-face{font-family:"Geist Fallback";src:local("Arial");font-weight:100 500;size-adjust:101.17%;ascent-override:99.33%;descent-override:29.16%;line-gap-override:0.00%}
@font-face{font-family:"Geist Fallback";src:local("Arial Bold");font-weight:600 900;size-adjust:99.45%;ascent-override:101.05%;descent-override:29.66%;line-gap-override:0.00%}
@font-face{font-family:"Geist Mono Fallback";src:local("Consolas");font-weight:100 500;size-adjust:109.13%;ascent-override:92.09%;descent-override:27.03%;line-gap-override:0.00%}
@font-face{font-family:"Geist Mono Fallback";src:local("Consolas Bold");font-weight:600 900;size-adjust:109.13%;ascent-override:92.09%;descent-override:27.03%;line-gap-override:0.00%}
```
Método: `size-adjust` = largura da mesma frase em Geist ÷ em Arial (por peso, 100 px); `ascent/descent` = `hhea` da Geist ÷ `size-adjust`. Conferência: altura de bloco **idêntica** em 14, 16, 18 e 40 px, em caixas de 343 e 600 px; largura de linha a ±0,2% (Geist) e ±0,1% (Mono). Um `@font-face` por peso porque o negrito sintético do Arial ficava 4,7% mais estreito que o Arial Bold.
Limite: medido com Arial/Consolas (Windows). No macOS o Arial existe (mesmo resultado); a mono cai em `ui-monospace`/Menlo sem métrica medida.

### 3.3 CSP (`scripts/csp.py`) — muda (autorizado pelo Pedro na Fase 2b)
`style-src 'self' 'unsafe-inline'` (sai `https://fonts.googleapis.com`) e `font-src 'self'` (sai `https://fonts.gstatic.com`). **O `tests/test_csp.py`, linhas 70 e 71, muda junto, com a autorização do Pedro** (2026-10-16): passa a esperar `style-src 'self' 'unsafe-inline'` e `font-src 'self'`. **Quem muda é a sessão do projeto, na implementação** (o design não mexe no projeto).

### 3.4 Uso
- Texto em Geist 400; nomes e valores em frase 500–600; títulos 600 com `letter-spacing: -.01em/-.02em`. Tamanho mínimo 12 px.
- **Mono só em número**, sempre com `font-variant-numeric: tabular-nums` (`.num`). Nome de arquivo ou código em texto vai em sans com fundo (`.cod`), nunca mono.
- Título do topo da landing: SVG pixelado 5×7 (não é fonte), com o texto em `.sr`.

## 4. Forma
- **Um conjunto para os dois temas:** cards 16 px, controles em pílula (999 px), navbar em pílula, moldura do mapa 20 px e o mapa 12 px. Por quê não 24 no claro e 12 no escuro: é um sistema só; a prancheta não pode parecer outro produto, e o raio é a assinatura mais visível depois da cor.
- Separação por linha (`--linha`), sem sombra; a única "sombra" é o anel de 6 px `--superficie` em volta da moldura do mapa no tema claro, que dá o respiro entre a página clara e o monitor escuro (D2.7).
- Toque mínimo 44 px em tudo; foco `2px solid var(--foco)` com 2 px de folga (na aba ativa, o anel é `--acao-ink` por dentro).

## 5. Páginas (375 e 1440 px) e estados

Referência: o protótipo. Ordem do HTML = ordem do celular.

### 5.1 Navbar flutuante (todas as páginas)
**A navbar final do site é: a marca (leva à landing) + Partidas + Jogadores + Prancheta. Não há botão de ação na navbar** (as ações ficam no topo da landing). "Marca", "Estados" e "Agente" são páginas de apoio do protótipo, acessíveis só pelo `indice.html` do protótipo; nunca entram no site.
Pílula `--superficie` com borda `--linha`, `position: sticky; top: 0` com 12 px de folga; marca (cabra C 30 px + wordmark liso 17 px) e os três links. Em ≤ 640 px: a pílula vira caixa de raio 24 com os links numa segunda linha que rola dentro dela. `--nav-h` = altura medida (§8).

### 5.2 Landing (`index.html`)
1. **Topo** (2 colunas em ≥ 761 px; 1 coluna em 375): título pixelado (SVG, `aria-hidden`, com `h1 .sr` "Cada round, explicado."), subtítulo de uma linha, **"Explorar partidas"** (principal, preto, leva à lista: é o que funciona hoje) e **"Adicionar demo"** (secundário, abre o painel §5.7), com a linha "Em breve · Envio de demo próprio. Por enquanto, explore as partidas do corpus." embaixo (decisão do Pedro na Fase 2b). À direita, o **agente** (§6). Textos do `PAGINA.landing.textos` (Python), nunca fixos no template.
2. **Três números** do `numeros_citaveis.json` (mono 34 px), 3 colunas ≥ 761, 1 em 375.
3. **Partidas**: filtros de origem (Profissionais · FACEIT · Todas) e de mapa (chips em pílula com contagem, rolam numa linha em 375); cards com mapa · evento, os dois times (nome, "venceu" invertido, placar em mono), a frase do decisor. 1/2/3 colunas (≥ 640, ≥ 1024). Vazio: "Nenhuma partida com esse filtro" + "Mostrar todos os mapas".
4. **Laterais em pontos** (≥ 1440 px), **pontos soltos, sem moldura** (escolha da Fase 2b; comparação em `capturas/cards-mapa-1440-opcoes.png`, a 1440 e 1920 px): o mapa em pontos ocupa **100% da largura útil** da lateral, centralizado na altura do topo (caixa de 480 px a partir de 96 px), com o nome do mapa embaixo (12 px `--apagado`). Decorativo, `aria-hidden`, posição absoluta em `left/right: 16px`, largura útil `clamp(104px, (100vw − 1180px)/2 − 32px, 300px)` (104 px a 1440; 300 px a partir de ~1950), `overflow-x: clip` no contêiner (não empurra nada; sem rolagem: medido). Descartado: o card com moldura (o mapa quadrado num card alto deixa o card vazio em cima e embaixo, e a 1440 px a moldura come 16 px da largura útil, que já é de 104 px).
5. **Rodapé** com a linha de terceiros (mapas, agentes e derivados da Valve, sem fins comerciais; fontes OFL).

### 5.3 Partida (`partida.html`, tema claro)
- Cabeçalho: migalhas (links de 44 px), `h1` placar HUD com etiqueta "começou CT/TR" (único uso da cor de lado na identidade) e "venceu" invertido; linha do decisor.
- **Abas** (Resumo · Replay · Jogadores · Placar · Perfil · Estilos) com gooey (§7), `sticky` logo abaixo da navbar (`top: calc(var(--nav-h) + 4px)`), rolam dentro da própria caixa em 375. Hash na URL.
- **Resumo:** card decisivo (número mono 56 px `--decisivo`, borda superior 2 px), MVP com "erro típico contra o rating oficial: {erro_rating}" em texto, round mais impressionante com pesos.
- **Replay (D6):** faixa de rounds em pílulas de 44 px (barra inferior na cor do lado que venceu, losango `--decisivo`, separador no meio-tempo); **moldura** `--radar` (raio 20, anel `--superficie` 6 px) com o mapa (canvas) `min(100%, 640px, 100svh − reserva)` (reserva 500/340 px) e o **transporte `sticky; bottom: 0`** dentro da moldura (A1); legenda com os glifos; times à esquerda e à direita (200 px) em ≥ 1024, embaixo em 375; eventos em linhas leves de 44 px (futuro `--tinta-2`, atual `--superficie-2`).
- **Jogadores:** tabela com 1ª coluna fixa, cabeçalhos-botão de 44 px; grupos `details` fechados com o destaque na linha (`localStorage`, como hoje).
- **Placar:** linha `--tinta-2`, bolinha na cor do lado vencedor do round, losango decisivo.
- **Perfil (D5):** §5.4. **Estilos:** cards com etiquetas `.tag.neutro` / `.tag.decisivo`.
- **Carregando** (`?estado=carregando` no protótipo): máscara de pontos do mapa da partida revelada da esquerda para a direita pelo **progresso real** (`clip-path: inset(0 calc(100% − var(--p)) 0 0)`), com "Carregando a partida… 62%" (`role="status"`). Com reduzir movimento, a mesma coisa sem transição.

### 5.4 Perfil (C5 e D5)
Ordem: seletor de jogador (pílulas que rolam) → cabeçalho (nick 40 px, time + "começou CT/TR", função por lado com "tendência", rating com erro típico, uma frase) → **Pontos a melhorar** → **Pontos fortes** → **Comparar com** → mini-radar → **Detalhes** (fechado).

**Pontos a melhorar só mostram tipos validados** (`TIPOS_DE_ERRO_VALIDADOS`, hoje vazio):
- **Estado vazio (o de hoje):** bloco tracejado com `.tag.neutro.validacao` "em validação" e o texto **"Ainda estamos conferindo estas leituras com partidas reais. Elas aparecem aqui quando estiverem validadas."** + link "Como é conferido". Nenhum número.
- **Com 1 a 3 tipos validados:** cards da §19.1 (`parser-cs2.md`), com **nome e frases de `metrics/erros.py`** (lido em 2026-10-15): `TITULOS` ("Não trocou o aliado", "Possível bait", "Perdeu a troca", "Morreu sozinho", "Primeira morte sem troca", "Flash no time", "Dano de utilidade no time"), `MOTIVO_EXPLICITO`, `COMO_MELHORAR`, `CONFERIR_COM_O_TIME`, `ROTULO_DO_NIVEL`. Exemplo no protótipo (fictício, marcado): "Não trocou o aliado" (explícito) e "Morreu sozinho" (depende da tática, com "o dado mostra posição e tempo, não o que o time pediu. Vale conferir com o time se era o plano."). **Saem** "Mortes sem troca", "Granadas sem efeito" e "Entradas sem apoio" (não são tipos do projeto; a troca é decidida pelo fato, não pela distância).
- Erro de jogador sem `--erro` e sem `--aviso` (barra cheia `--tinta` / tracejada `--apagado`).
- No protótipo, **todo número de jogador leva a etiqueta "dados de exemplo"**.

**Comparação lado a lado:** grupos Impacto (rating, ADR, KAST, abates/mortes), Abertura (primeiros contatos ganhos e perdidos), Trocas (trocou, foi trocado, não trocou, perdeu a troca), Utilidade (cegueira imposta, dano de utilidade, flash no time), Situações (clutches, pós-plant, retake). Cada linha: valor + bruto, referência anônima do corpus para a função, **quem está melhor escrito** ("kairo à frente", "empate na prática", "amostra pequena · sem comparação") e chips "R12 · 1:14" que abrem o Replay (§19.3). Sem economia; sem radar/aranha. **375 px:** um jogador por vez (o seletor no topo) e o outro **em linha** embaixo do valor ("brisa: 1,18"); a coluna "quem está melhor" e os chips descem para baixo da métrica.

**Mini-radar:** ajuda. Bolinha = abate, losango = morte, na cor do lado do round, cada ponto é um link de 44 px para o Replay no instante, sobre o mesmo radar processado (escuro também no claro). Acima de ~30 pontos, agrupar por região.

### 5.5 Prancheta (`prancheta.html`, escuro violeta, D7)
A §14 inteira com os tokens do escuro: cabeçalho (select com os dois grupos de mapas, linha de origem, **Reproduzir** com o degradê quente, único por tela), barra de cima em pílulas, linha de dica (`role=status`, `--superficie-2`), mapa na moldura com relógio 42 px e avisos (`▲` `--aviso` "+2,3 s"), painel com abas gooey (Jogadores · Granadas · Tática · Grupo), linha do tempo `--tl-fundo` (rola dentro em 375), roteiro. **Pontinhos de status** (`.ponto-status`): online (cheio `--decisivo`), offline (vazio), atrasado (`--aviso` + "+2,3 s"), em validação (pontilhado) — sempre com a palavra.

### 5.6 Jogadores (`jogadores.html`, claro)
Aviso de corpus, chips de mapa e lado, pílulas A/B/C em cinza (a cor tem dono), cards com barra de intervalo (assimétrica permitida), referência tracejada da função, bruto ao lado; abaixo do mínimo, só o bruto + "amostra pequena".

### 5.7 "Adicionar demo" (decisão 3)
`<dialog>` com foco no "Fechar", Esc e clique fora fecham, foco volta ao botão. Painel honesto: etiqueta "Em breve", "O envio de demo próprio ainda não está disponível.", como funciona hoje e como sugerir (issue no GitHub), botão "Explorar partidas". Embaixo, **o estado futuro desenhado** (só forma): Escolher (área de soltar `.dem`, botão desativado), Enviando (barra `role=progressbar` 62%), Erro (`--erro`, ✕ "Erro:", `role=alert`).

## 6. Agente CT/TR em listras (C4, gravação do Pedro)

> **[HISTÓRICO, superado pelos blocos "RODADA FINAL", "ESCOLHA" e "AGENTES APROVADOS" abaixo] Estado (Fase 2b, 2026-10-16): em escolha.** A versão da Fase 2 não passou no reconhecimento a 200 px (CT e TR). O pipeline mudou (§6.1) e há **três variações de parâmetros por agente** para o Pedro escolher: `capturas/agentes-variacoes-ct.png` e `capturas/agentes-variacoes-tr.png` (200 e 320 px, fundo claro da landing, parâmetros escritos embaixo). **Loop, peso e custo por quadro só são finalizados depois da escolha**; os limites continuam: ≤ 120 KB por agente, nunca o LCP, CLS 0, custo medido a CPU 4×. Os números da §6.3 são da versão da Fase 2 e serão refeitos.

> **[HISTÓRICO: profundidade descartada] Rodada de profundidade (2026-10-16).** Base V3 (decisão do Pedro). Folhas de 4 colunas (V3 de hoje; V3 + profundidade 0,3; 0,5; 0,7), a 200 e 320 px: `capturas/agentes-profundidade-ct.png` e `capturas/agentes-profundidade-tr.png`; GIFs do trecho (vai e volta, 15 fps): `capturas/agente-ct-profundidade.gif` (2,4 s, k 0,5) e `capturas/agente-tr-profundidade.gif` (2,1 s, k 0,5). Gerador: `agente-pipeline/profundidade.py`.
> - **Como o gato da R5 ganha volume** (olhado de novo em 2026-10-16): as linhas são retas e finas, não se curvam; o volume vem do **tom** (linha cinza-clara no lado iluminado, escura e mais cheia na sombra) e de poucos **acentos escuros** curtos (olhos, orelhas, patas); a borda **se dissolve num halo claro** e em **linhas soltas que continuam fora da silhueta** (o chão e o fundo), então a figura não parece recortada.
> - **Profundidade:** Depth Anything V2 **Small** (ONNX, Apache-2.0) por quadro, normalizado com os mesmos percentis no trecho, desfoque espacial e **suavização no tempo** (gaussiana de 1,5 quadro, em ciclo); a linha sobe onde a superfície está mais perto (`desloc = −k × passo × (2·prof − 1)`). Tremor do deslocamento entre quadros a 320 px: 0,05 px × k (sem suavizar 0,10 × k); não foi preciso o mapa médio.
> - **Luz:** normal da superfície pelo gradiente da profundidade, luz de cima e da esquerda; perto da borda de fora, a linha fica até 55% mais fina onde a superfície está de costas para a luz. **Bordas soltas:** 45% das linhas ganham um traço curto (3–9 px a 200 px) logo por fora da borda, com sorteio fixo por linha (não pisca); o contorno de dentro continua fechado.
> - **Arma do CT:** contorno da M4A4 com **SlimSAM-77** (ONNX, Apache-2.0) por pontos no quadro de 6,0 s, limitado por um **corredor desenhado à mão** em volta da arma (o SAM vazava para o ombro e o colete), acompanhado nos outros quadros por **ECC** (rotação + translação do cinza dentro da arma), conferido sobre o vídeo cortado acima do cartão em 5,4, 6,0 e 6,6 s; **folga de uma linha** sem nada desenhado em volta; **CLAHE 3,0 só dentro da arma**; o contorno fino desta rodada **saiu** depois (decisão do Pedro, ver a quinta coluna). **Trecho do CT: 5,4–6,6 s** (o de 9,0–12,5 s não foi preciso: com o contorno, a arma lê a 200 px). TR sem contorno de arma.
> - **Modelos (manifesto §6.4):** `depth-anything-v2-small/model.onnx` (onnx-community/depth-anything-v2-small, Apache-2.0, 99.060.839 B, sha256 `afb6a5c2…df10c`); `slimsam-77-uniform/vision_encoder.onnx` (23.276.014 B, sha256 `9f843327…366d0`) e `prompt_encoder_mask_decoder.onnx` (16.557.892 B, sha256 `f4514391…43b5bb`) (Xenova/slimsam-77-uniform, Apache-2.0); recorte `isnet-general-use.onnx` (rembg, sha256 `60920e99…c0d964a`). Ficam no cache do usuário (`~/.cache/modelos-goat/` e `~/.rembg/models/`), fora do projeto e do repositório.

> **[HISTÓRICO: a coluna 5 virou a TRV1, com halo e linhas soltas que saíram] Quinta coluna, "estilo gato" (2026-10-16).** Folhas com duas colunas (0,5 de hoje e 5), a 200 e 320 px: `capturas/agentes-gato-ct.png` e `capturas/agentes-gato-tr.png`; GIFs da coluna 5: `capturas/agente-ct-gato.gif` (2,4 s) e `capturas/agente-tr-gato.gif` (2,1 s).
> - **Arma do CT nas duas colunas: sem linha de contorno** (decisão do Pedro); em listras, separada do corpo só pela folga vazia de uma linha do recorte do SlimSAM; as luvas (SlimSAM por um ponto em cada mão) saem da máscara da arma e viram listras como o resto da mão.
> - **Coluna 5:** linhas retas (sem profundidade); volume pelo **tom** — três cinzas da tinta do tema sobre o fundo (`--tinta` a 58% = `#717171`, 80% = `#3b3b3b`, 100% = `#0a0a0a`) — com a espessura só ajudando (0,36/0,46/0,62 do passo + 0,10 × tom, mínimo 1,15 px na tela); **acentos escuros** curtos tirados do dado (as manchas mais escuras em relação à vizinhança, ≥ 40 px, só no rosto — os 22% de cima do agente — e nas mãos); **halo**: a faixa da borda vira linha clara, contorno fechado; linhas soltas fora da borda (45% das linhas, e 35% delas com uma segunda mais longe, no fundo).
> - **Contraste medido da linha mais clara desenhada** (miolo da linha, 95º percentil das linhas claras, depois do antisserrilhado, contra `#ffffff`): **3,59:1 a 200 px** e **4,95:1 a 320 px** (PASSA 3:1). Sem o mínimo de 1,15 px, a 200 px dava 2,55:1 (reprovava).
> - **Histórico:** para rever a R5, a página foi aberta pelo navegador (Playwright), porque o acesso direto passava pelo checkpoint da Vercel; uma imagem baixada antes era de outro post (errada) e foi apagada do scratchpad, como a captura da página.

> **RODADA FINAL (2026-10-19), em escolha do Pedro.** O **estilo gato (coluna 5) venceu**. A profundidade saiu: o **Depth Anything V2 Small deixou o manifesto e o `converte_agente.py`** (§6.4). Folhas: `capturas/agentes-final-tr.png` (TRV1 × TR refinado) e `capturas/agentes-final-ct.png` (CT-A × CT-B), a 120, 200 e 320 px, com os parâmetros embaixo; pares a 200 px: `capturas/agentes-final-par-tr-ct-a.png` e `capturas/agentes-final-par-tr-ct-b.png`; GIFs: `capturas/agente-tr-refinado.gif`, `capturas/agente-ct-a.gif`, `capturas/agente-ct-b.gif`. Arquivos gerados em `agentes/rodada-final/` (`.js`, quadro fixo em SVG, prévias, `registro-*.txt`, `medidas-*.json`).
> - **Regra da TRV1 (obrigatória):** o TR da coluna 5, como foi entregue em 2026-10-16, está congelado em `agentes/TRV1/` (sha256 de cada arquivo em `SHA256SUMS.txt`; gerado com o `converte_agente.py` do commit `2962bdb`). **A TRV1 nunca é sobrescrita.** Se a rodada der errado (o TR refinado ficar pior, ou nenhum CT passar), **a landing usa só a TRV1, sem sorteio**, até o Pedro decidir outra coisa.
> - **Regra do sorteio:** **passou a valer em 2026-10-19**, com o CT-A aprovado pelo Pedro (ver "AGENTES APROVADOS"). Se um dia o CT for reprovado ou retirado, a landing volta a mostrar só o TR (ou a TRV1), sem `Math.random`.
> - **Pipeline novo, igual para TR e CT:** (1) **nada fora da silhueta**: nenhum segmento fora da máscara do agente dilatada em 1 px (0 px nos três, a 120, 200 e 320 px); o halo e as linhas soltas da coluna 5 saíram; (2) **arma inteira no tom mais escuro** com espessura mínima, pela máscara do SlimSAM, sem contorno; (3) **30 quadros por segundo**, tom e espessura suavizados no tempo (gaussiana de 1,5 quadro, média efetiva de ~5), tons com histerese; (4) **4 tons** da tinta (60, 74, 88 e 100%), linha mais clara a **3,79–3,95:1 a 200 px**; (5) olhos e boca da balaclava como falhas claras, calça com contraste local (CLAHE por região), colete separado por tom; (6) **loop**: o TR fecha com **transição cruzada** nos 0,40 s finais (3,00 s); os CT fecham em **vai-e-volta suave** (cosseno, sem parada seca); (7) caixa 3/4 com a mesma proporção (0,95) para todos.
> - **Privacidade:** cada quadro é cortado acima do cartão do jogador **na memória**, antes de qualquer gravação (TR e CT-B em y < 590; CT-A em y < 545). Nada bruto sai de `fonte-agente/`. Conferido em quadros espalhados pelo trecho inteiro: nenhum arquivo entregue mostra nick, avatar, nível ou patente.
> - **Mãos do CT-A:** a máscara de mãos do SlimSAM leva as luvas ao tom escuro preservando os dedos (ajuste de tom de região real, nada desenhado).
> - **Números (medidos em 2026-10-19):** tabela em §6.3.

> **ESCOLHA DO PEDRO (2026-10-19): o TR refinado é o agente TR; o CT-B saiu; o CT-A segue com um ajuste só na cabeça (lentes e filtro).** A TRV1 continua congelada e intacta em `agentes/TRV1/` (reserva). Os vídeos do CT-B ficam em `fonte-agente/`, sem uso. O Depth Anything V2 Small foi apagado do cache do Pedro (o SlimSAM fica).
> - **Manifesto do agente TR (`agentes/rodada-final/agente-tr.js` = `prototipo/agente/agente-tr.js`):** fonte `fonte-agente/agente-tr-menu.mp4` (sha256 `4d1f75489d2f4f6a92ad71b94c9b9ab4bc97b6e0c4b69b22bc3ec6352337b615`); trecho 0,6 a 4,2 s (+0,4 s de transição cruzada), 30 fps, 90 quadros, loop de 3,00 s; quadro de referência 2,5 s; corte de privacidade y < 590; `agente-tr.js` sha256 `857fb00c859b2d0c78a89ce729e1b51dc9bd004d4c9bba249e8550c984cb20dd` (223.263 B; 60.472 B gzip -9); parâmetros: 77 linhas × 240 colunas, 4 tons (60/74/88/100%), espessura 0,42/0,48/0,56/0,66 do passo (arma fina: só o mínimo de 1,2 px), cortes de tom 0,30/0,52/0,74 com histerese 0,04, suavização no tempo de 1,5 quadro, aspecto 0,95, arma por SlimSAM com os pontos `260,305;380,355;420,420;470,385;540,425;600,450;628,463`, mãos `300,360;520,400`; modelos: `isnet-general-use.onnx` e SlimSAM-77 (sha256 acima, §6.4). Gerador: `agente-pipeline/converte_agente.py`.
> **AGENTES APROVADOS (2026-10-19): o par fechado é TR refinado + CT-A com a cabeça ajustada.** A TRV1 fica como **reserva** congelada (`agentes/TRV1/`, nunca sobrescrita). O CT-B e o CT-A sem ajuste ficam só como histórico (`agentes/rodada-final/`, `capturas/agente-ct-b.gif`). Folha do ajuste: `capturas/agentes-final-ct-a-cabeca.png`; par: `capturas/agentes-final-par-tr-ct-a-cabeca.png`; GIF: `capturas/agente-ct-a-cabeca.gif`.
> - **A regra do sorteio vale agora:** a cada visita, CT ou TR (`Math.random() < 0,5`), **só o arquivo do lado sorteado é baixado** (depois do `load`, com `requestIdleCallback`); os dois usam a **mesma caixa** (`aspect-ratio: 251/264`), então o sorteio não mexe no layout; a **linha de base** usa `--ct` ou `--tr` conforme o lado; alts **"Agente CT com fuzil"** e **"Agente TR com fuzil"**; **com reduzir movimento o sorteio continua, só com o quadro fixo**; **sem JavaScript aparece o quadro fixo do TR (o padrão: aprovado primeiro e lê melhor a 200 px)**. Os dois quadros fixos em SVG ficam no HTML (o do CT escondido até o script de sorteio, que roda antes do primeiro desenho). `?agente=ct|tr` força o lado (teste).
> - **Manifesto do agente CT (`agentes/ct-a-cabeca/agente-ct-a.js` = `prototipo/agente/agente-ct.js`; dentro do arquivo o nome é `CT-A`):** fonte `fonte-agente/agente-ct-inspecao-claro.mp4` (sha256 `6f047147e14d83d19a12b84097dd5dde9bc3a01067ddde5de4d7ac208f874321`; inspeção, galpão claro, M4A4); trecho 3,2 a 5,4 s, 30 fps, 67 quadros, quadro de referência 4,3 s, vai-e-volta suave (cosseno, fator 1,15), ciclo de 5,07 s, 77 quadros guardados; corte de privacidade y < 545; `.js` sha256 `a71af4e0b29258360d9e884ebcd62f2d61076e46d5764a62652d7fcc0c023317` (232.444 B; 34.074 B gzip -9); parâmetros: 77 linhas × 240 colunas, 4 tons (60/74/88/100%), espessura 0,42/0,48/0,56/0,66, suavização 1,5 quadro, aspecto 0,95, arma (SlimSAM) `120,275;300,235;320,290;380,215;450,190;470,186`, mãos (SlimSAM, escurecidas: `--maos-escuras`) `240,280;410,225`, lentes `305,86;349,95`, filtro `321,134`, `--cabeca 23`, corpo (linhas 23 a 76) tirado byte a byte do `.js` da rodada final (sha256 `1560be31d437cd9edf5d8d3651d18b81c1f64a5516fc992b55d446f4bdc7337c`) porque a máscara da arma não se reproduz bit a bit (os pontos negativos daquela rodada não foram registrados). Modelos: `isnet-general-use.onnx` e **SlimSAM-77, que ficam no cache e no manifesto** (só são usados se alguém regenerar os agentes). Gerador: `agente-pipeline/converte_agente.py`.
> - **CT-A finalizado:** trafega ~34 KB (33.704 B gzip -9; 34.377 B medidos servindo com gzip -6); tinta que muda entre quadros 0,7% de média e 1,8% de máximo; custo por quadro, CPU 4×, na landing: 0,93 ms (375 px) e 0,88 ms (1440 px) (TR: 0,68 e 0,78 ms), limite 4 ms; 0 px fora da silhueta a 120, 200 e 320 px; linha mais clara 3,79:1 a 200 px.
> - **Landing com o sorteio (375 e 1440 px, Fast 4G 9/1,5 Mbit 165 ms, CPU 4×, 5 rodadas, HTTP com gzip):** LCP mediana em ms, fonte normal / bloqueada: 375 px TR 680 / 712, CT 704 / 704; 1440 px TR 768 / 740, CT 744 / 752 (piores: 920 e 1100). **O elemento do LCP é o subtítulo (`P.sub`) nos 8 casos.** CLS: 0,0000 em todos a 375 px; a 1440 px 0,0065 com a fonte normal (igual nos dois lados, e 0,0000 com a fonte bloqueada: vem da troca de fonte, não do agente nem do sorteio; é o mesmo valor da Fase 2, 0,0066, e está abaixo do limite de 0,1 do §6.3; a meta 0 vale para o agente, que tem caixa fixa). **Verificado também:** reduzir movimento a 375 px sorteia o CT e desenha 1 quadro; sem JS, quadro fixo do TR, alt "Agente TR com fuzil".
> - **Pendência da sessão do projeto:** depois do **primeiro deploy**, repetir o teste do `Content-Encoding` com o `agente-tr.js` e o `agente-ct.js` publicados (`curl -sI -H "Accept-Encoding: gzip, br" <url>`); hoje só o gzip do GitHub Pages foi confirmado em outros `.js` do Pages, e o brotli não é servido.

> - **Peso que trafega e entrega (verificado em 2026-10-19):** o GitHub Pages serve `.html` comprimido (`Content-Encoding: gzip`, conferido em `pedroppansani.github.io/parser-replay-cs2/`) e `application/javascript` comprimido (`Content-Encoding: gzip`, conferido num `.js` de outro site do Pages, `pages.github.com/js/application.js`, porque o site do Pedro ainda não publica nenhum `.js`). **Só gzip, sem brotli.** O TR trafega ~61 KB (medido servindo com gzip -6: 61.181 B), dentro de 120 KB. Refazer o teste no `.js` do agente depois do primeiro deploy.
> - **LCP e CLS da landing só com o TR (375 px, Fast 4G 9/1,5 Mbit 165 ms, CPU 4×, 5 rodadas, servida por HTTP com gzip):** fonte normal LCP mediana 792 ms (pior 800), CLS 0,0000; fonte bloqueada LCP 744 ms (pior 896), CLS 0,0000; a 1440 px: LCP 680/752 ms, CLS 0,0065/0,0000. **O elemento do LCP é o subtítulo (`P.sub`) em todos os casos**, nunca o agente.

### 6.1 Produção — `agente-pipeline/converte_agente.py` (loop e saída) e `agente-pipeline/variacoes.py` (parâmetros)
> **O pipeline em vigor é o da rodada final (bloco "RODADA FINAL" acima, `converte_agente.py`): os itens 4 a 7 e a tabela de variações abaixo são o histórico da Fase 2b (`variacoes.py`).** Os itens 1 a 3 (privacidade, recorte, caixa 3/4) continuam valendo.

1. **Privacidade (obrigatório):** cada quadro é cortado em `y < 590` **na memória, logo depois de decodificado** (o cartão do jogador começa abaixo de ~600 no recorte 760×1028). Nenhum quadro bruto é gravado em disco. Os vídeos ficam só em `fonte-agente/` (fora do git).
2. **Recorte:** rembg `isnet-general-use` (local); só o maior pedaço conexo (sai o cursor do mouse); alfa com mediana de 3 quadros e erosão de 1 px (sem halo).
3. **Enquadramento 3/4:** da cabeça ao corte (meio da coxa); folga de 8% em cima e nos lados; a **mesma caixa** nos dois (aspecto 0,95); arma inteira com folga ≥ 8 px a 120 px.
4. **Antes das listras (Fase 2b):** o fundo é trocado pela mediana do agente (o fundo claro não entra no contraste); **filtro bilateral** (tira a textura do tecido, preserva as bordas); **CLAHE** (contraste local; no rosto, o primeiro 22% do agente, limite 1,6× e grade 4×4: lentes e filtro da máscara do CT, buracos da balaclava do TR); tons **equalizados** dentro do agente (posto no histograma).
5. **Listras (Fase 2b):** a **espessura** da linha varia com a luminância (escuro = mais grossa: `t = tmin + (tmax − tmin) × escuro^gama`, em fração do passo) e a linha só some abaixo do "corte" (claro de verdade); segmentos **< 3 px a 200 px** descartados e **falhas de 1 px** emendadas; **55 a 75 linhas na figura a 200 px**; **contorno fechado** (numa faixa de 2 px junto da borda de fora a linha nunca some e tem a espessura mínima "borda"); opção de **passo pela metade na cabeça**; opção de **arestas internas** (Canny) virando falha, para a arma se separar do uniforme. Uma cor só (`--tinta`); o acento do lado é **só a linha de base** (`--ct`/`--tr`), confirmado pelo Pedro.
6. **Loop "respiração parada":** assinatura de movimento dentro do agente; loop direto se a costura ≤ 1,5× o passo típico, senão vai-e-volta de um trecho calmo. **CT: trecho de 5,5 a 6,5 s do vídeo**: a M4A4 está mais baixa e atravessa o peito, coronha à esquerda e cano à direita da máscara, sem passar por trás da cabeça (em 3–4 s, 15–17 s e 20–21 s o cano sobe até a altura da máscara; em 7,0–7,5 s a cabeça vira). As variações usam o quadro de 6,0 s; a calma do trecho é medida na finalização. **TR:** quadro de 8,2 s (trecho calmo 8,2–9,1 s, fora dos giros da arma).
7. **Formato:** segmentos em binário compacto (base64) num `.js` + o quadro fixo do CT em SVG em linha. Com a espessura variável, o segmento ganha a espessura (por trecho) e o tocador desenha polígonos; a comparação com o sprite WebP é refeita na finalização.

**As três variações (as mesmas para CT e TR):**

| | linhas na figura a 200 px | espessura (fração do passo) | gama | some abaixo de | borda fechada | bilateral (d, cor, espaço) | CLAHE (rosto ×1,6) | arestas internas | passo na cabeça |
|---|---|---|---|---|---|---|---|---|---|
| V1 · silhueta forte | 57 | 0,10–0,78 | 2,0 | 0,16 | 0,60 | 15, 75, 9 | 3,0 | não | ×0,5 |
| V2 · arestas | 63 | 0,08–0,72 | 1,5 | 0,14 | 0,55 | 11, 60, 7 | 2,5 | Canny 80/180 | ×0,5 |
| V3 · tons | 71 | 0,12–0,70 | 1,0 | 0,20 | 0,60 | 15, 90, 9 | 2,0 | não | ×1 |

### 6.2 Na página
```html
<figure class="agente" id="agente" data-lado="tr" data-base="agente/" role="img" aria-label="Agente TR com fuzil">
  <svg aria-hidden="true">…quadro fixo do TR…</svg><canvas aria-hidden="true"></canvas><span class="corte" aria-hidden="true"></span>
</figure>
<!-- sem sorteio enquanto nenhum CT estiver aprovado; depois: script antes do primeiro desenho (data-lado ct|tr, aria-label do lado, esconde o SVG do outro) -->
```
- Caixa fixa `aspect-ratio: 251/264`, largura `min(100%, 300px)` (`min(70%, 240px)` em ≤ 760 px): **CLS 0** com qualquer lado.
- `js/agente.js` baixa **só** `agente-<lado>.js`, depois do `load` e com `requestIdleCallback`; desenha o quadro 0, troca o SVG pelo canvas e toca a 30 fps (o `fps` do arquivo); pausa fora da tela e com a aba escondida.
- **Sem JS:** o SVG do quadro fixo (hoje o do TR, "Agente TR com fuzil"). **Reduzir movimento:** só o quadro fixo (com um CT aprovado, o sorteio continua).
- **Hoje:** o sorteio vale (CT-A e TR aprovados em 2026-10-19), como no bloco "AGENTES APROVADOS" acima. `js/agente.js` mapeia `ct` → agente `CT-A` do arquivo `agente-ct.js`. O formato novo do `.js` (tom + deslocamento por segmento, `opac`, `esp`) é tocado por `js/agente.js` do protótipo.
- O agente **nunca é o LCP** e nunca entra na marca, no favicon nem no compartilhamento.

### 6.3 Orçamento e medidas (agentes finais, 2026-10-21; custo por quadro medido na landing do protótipo, CPU 4×, Chrome)
| | TR refinado (`agente-tr.js`) | CT-A com a cabeça ajustada (`agente-ct.js`) | TRV1 (reserva, congelada) | limite |
|---|---|---|---|---|
| peso | 223.263 B; **trafega 61.181 B** (gzip -6) | 232.444 B; **trafega 34.377 B** (gzip -6) | `agente-trv1-sprite.webp` 112.444 B | 120 KB que trafegam, por agente |
| custo por quadro, CPU 4× (375 · 1440 px) | 0,68 · 0,78 ms | 0,93 · 0,88 ms | não comparável (só o `drawImage` do sprite) | ≤ 4 ms |
| tinta que muda entre quadros (média · máx.) | 2,2% · 6,6% | 0,7% · 1,8% | 4,8% · 5,6% (a 15 fps) | média ≤ 3% |
| linha mais clara a 200 px | 3,95:1 | 3,84:1 | 3,59:1 | ≥ 3:1 |
| fora da silhueta (120 · 200 · 320 px) | 0 px | 0 px | tem linhas soltas (estilo da época) | 0 px |
| loop | 3,00 s, transição cruzada nos 0,40 s finais | vai-e-volta suave (cosseno), janela 2,20 s, ciclo 5,07 s | vai e volta, 2,13 s, parada na virada | |
| quadros / fps | 90 / 30 | 77 / 30 | 17 únicos / 15 | |

- **Landing com o sorteio:** LCP e CLS no bloco "AGENTES APROVADOS" acima. **CLS de 0,0065 a 1440 px com a fonte normal: aceito pelo Pedro em 2026-10-21** (vem da troca de fonte, não do agente; abaixo do limite de 0,1).
- **Histórico, sem uso:** o CT-B (XM1014) e o CT-A antes do ajuste da cabeça ficam em `agentes/rodada-final/`. O CT-B não fechou a meta de tinta (3,5% de média; só desacelerando o vai-e-volta chegava a 3,0% com ~97 KB ou 2,4% com ~114 KB).

### 6.4 Onde ficam os arquivos do agente no projeto (confirmação do Pedro, item 11)
- Os **`.js` gerados** de cada agente **entram no repositório**, em `dashboard/web/`, junto dos outros recursos da página (são o próprio recurso; ~22 KB e ~10 KB na versão da Fase 2).
- O **`converte_agente.py` entra no repositório em `scripts/`**, mas **não roda no build**: é rodado à mão, só quando a fonte ou os parâmetros mudarem.
- **Manifesto** ao lado dos `.js` (ex.: `dashboard/web/agentes.manifesto.json`) com: o **sha256 do vídeo de origem**; o **nome e o sha256 do modelo** (`isnet-general-use.onnx`); os **parâmetros**; o **trecho do vídeo usado** (segundos e quadros); o **sha256 de cada `.js`**.
- **Um teste** confere que os `.js` batem com o manifesto (sha256).
- **Modelos no manifesto** (todos Apache-2.0, fora do repositório, no cache do usuário):
  - recorte: `isnet-general-use.onnx` (rembg), sha256 `60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a`;
  - ~~profundidade (Depth Anything V2 Small)~~ **removido do manifesto e do `converte_agente.py` em 2026-10-19** (o estilo gato venceu; o `profundidade.py` fica só como histórico da R5). O arquivo `~/.cache/modelos-goat/depth-anything-v2-small/` pode ser apagado do cache do Pedro (ação dele);
  - arma e mãos: **SlimSAM-77** (`Xenova/slimsam-77-uniform`, `vision_encoder.onnx` 23.276.014 B + `prompt_encoder_mask_decoder.onnx` 16.557.892 B ≈ 40 MB), sha256 `9f8433273a6750b587779baa0cf5508111001bf7e7acfcf585d370139fd366d0` e `f4514391764fbd56e08e119060d874ecd7d52994bfb1968af159e12d4943b5bb`, em `~/.cache/modelos-goat/slimsam-77-uniform/`.
- O vídeo e o modelo ficam **fora do repositório**. O manifesto diz onde ficam na máquina do Pedro, sem caminho pessoal além de `TimeIA\...` (vídeos: `TimeIA\Iriun\Sites\Base-Design\prototipos\parser-cs2-v2\fonte-agente\agente-tr-menu.mp4` e o do CT aprovado, `...agente-ct-inspecao-claro.mp4` (CT-A) ou `...agente-ct-menu-galpao-xm1014.mp4` (CT-B); modelo: o cache do rembg do usuário, identificado só pelo nome e pelo sha256).

## 7. Abas gooey (R4, C1)
- Duas camadas: `.goo` (fundo, `aria-hidden`: pílula `--superficie-2` + bolha `--acao`) e os `[role=tab]` por cima, sem filtro.
- **O filtro só existe durante a transição:** a classe `.movendo` liga `filter:url(#goo)` quando a bolha começa a andar e sai no `transitionend` (ou 420 ms). Em repouso o `filter` computado é `none` e a pílula é nítida (prova: `capturas/c1-pilula-repouso-4x.png`).
- Filtro: `feGaussianBlur stdDeviation 4` + `feColorMatrix` alfa `28 −12`. Movimento: `transform` e `width` em 220 ms, `cubic-bezier(.3,1.25,.5,1)`.
- Teclado: setas, Home, End, `tabindex` móvel, foco visível. **Reduzir movimento:** troca seca, sem filtro em nenhum momento (medido).

## 8. Navbar nunca cobre âncora nem foco (C2)
- `html { scroll-padding-top: calc(var(--nav-h) + 16px) }`, com `--nav-h` = altura real da navbar (o JS mede no início e com `ResizeObserver`).
- `focusin`: se o elemento focado cruzar o retângulo da navbar, a página rola até ele ficar 16 px abaixo dela (cobre o foco por Tab em qualquer posição de rolagem).
- As abas da partida grudam abaixo da navbar (`top: calc(var(--nav-h) + 4px)`).
- Teste no `aceite_fase2.py`: Tab 70 vezes em cada página, a partir de uma posição rolada, em 375, 768 e 1440 px; âncora `#partidas`; "Pular para o conteúdo". Coberto = cruza a navbar **e** `elementFromPoint` no foco não é o elemento. **0 ocorrências.**

## 9. Mapas em pontos
- `prototipos/parser-cs2-v2/gera_pontos.py <radar> <saida.webp> 64 8`: 64×64 células, ponto pela luminância, fundo do radar fora; WebP só alfa, **1,9 KB (Mirage) e 2,1 KB (Dust II)**. Gerado no build a partir dos radares que já estão no projeto (decisão 7).
- Usos que ficam: laterais ≥ 1440 px (`mask-image` em `data:` dentro do CSS — em `file://` a máscara por URL de arquivo não é garantida), carregamento (§5.3), imagem de compartilhamento 1200×630 (`gera_og.py`: pontos + placar + marca; 69 KB PNG; sem agente, sem marca Valve). Saem: seletor de mapa, prancheta, 404, Grupo vazio.
- Brilho: degradê deslizando por `background-position` (9 s), parado com reduzir movimento.

## 10. O que muda em cada arquivo do projeto
- `dashboard/web/tokens.css`: dois blocos de tema (§2), tokens de forma, `@font-face` das fontes e dos fallbacks (§3). `metrics/paleta.py`: validar os dois temas e o grupo do mapa (regras do `paleta_v3.py`).
- `template.html`, `tactics.html`, landing do `build_site.py`, `jogadores.html`: `data-tema` (prancheta = escuro), navbar flutuante, abas gooey, componentes da §5; tirar os `<link>` do Google Fonts; ler cores do canvas dos tokens `*-mapa`.
- `map_core.js`: só a fonte do canvas (`Geist Mono` nos horários, `Geist` nos nomes) e as cores lidas de `--*-mapa`. Formas, anel duplo, RADAR_AJUSTE e a granada desenhada (A25) **não mudam**.
- `scripts/csp.py` e `tests/test_csp.py`: §3.3 (teste com OK do Pedro).
- Build: copiar `fontes/` (woff2 + `OFL.txt`) e `agente/` para `docs/`; rodar `gera_pontos.py` e `gera_og.py` sobre os radares do projeto; **não** rodar o `converte_agente.py` no build (§6.4): os `.js` gerados (`agente-tr.js`, `agente-ct.js`) e os quadros fixos em SVG vão prontos para o repositório.
- README, seção de terceiros: mapas, pontos, imagem de compartilhamento e agentes derivados do jogo da Valve, projeto sem fins comerciais; Geist/Geist Mono OFL.
- `leitura/perfil_erros.py` e o template do Perfil: estado vazio e textos da §5.4 (sem números quando `TIPOS_DE_ERRO_VALIDADOS` estiver vazio).

## 11. O que não pode mudar
Tudo da §12 do `parser-cs2.md`, mais: o canvas do mapa continua escuro e com as mesmas cores e formas; CT azul e TR dourado/laranja só para lado; erro de jogador sem `--erro`/`--aviso`; nada de radar/aranha; o agente nunca na marca; o cartão do jogador nunca em nenhum arquivo.

## 12. Critérios de aceite (medidos no protótipo, `file://` e HTTP local; Chrome via Playwright)

| # | Critério | Resultado no protótipo |
|---|---|---|
| A1 | Transporte do replay visível sem rolar | 1440×900: 836–880 · 375×667: 619–663 · 375×812: 764–808; `elementFromPoint` = botão; **PASSA** |
| A2 | Sem rolagem horizontal | 13 páginas/abas × 375/768/1440: **nenhuma** |
| A3 | Texto ≥ 4,5:1 (3:1 grande) contra o fundo efetivo, nos dois temas | 2.170 textos, **0 reprovados** |
| A4 | Marcas ≥ 3:1 | tokens: menor 3,27 (`--tr` sobre `--superficie-2`, claro) — PASSA |
| A5 | Toque ≥ 44×44 | **0** abaixo |
| A6 | 2 famílias, mono só em número | `Geist`, `Geist Mono` (+ fallbacks locais); nenhum elemento mono com palavra |
| A8 | Paleta | `paleta_v3.py` A claro, A escuro e mapa: **PASSA** |
| A9 | Abas por teclado | seta → próxima com foco e contorno; End/Home; **PASSA** |
| A12 | Landing LCP < 2,5 s, CLS < 0,1 (375, Fast 4G, CPU 4×) | (2026-10-19, agentes finais) fonte normal: **LCP 704 ms (CT) / 680 ms (TR), CLS 0** · fonte bloqueada (fallback): **704 / 712 ms, CLS 0**; maior elemento = subtítulo; 1440 px: LCP 744–768 ms, CLS 0,0065 (troca de fonte; 0 com a fonte bloqueada) |
| A13/A14/A25 | radar, anel duplo, granada desenhada | **inalterados**: o fundo do mapa continua `--radar #0f141b` e as cores do canvas são as mesmas; os valores da §4.1/§19.7 do `parser-cs2.md` continuam válidos. **Sem nova medição: aceito pelo Pedro** (Fase 2b) |
| A26 | CLS da partida e da prancheta < 0,1 | partida #resumo 0, #replay 0, prancheta 0 (375×667) |
| N1 | Agente: ≤ 120 KB por agente, nunca LCP, CLS 0 com o sorteio, custo ≤ 4 ms/quadro a 4× | (2026-10-19) CT-A 33,7 KB gzip, TR 60,5 KB gzip (≤ 120 KB; **o Pages só comprime com gzip: confirmar no primeiro deploy**); LCP = subtítulo nos 8 casos; CLS do agente 0 (a 1440 px, 0,0065 vem da fonte); 0,68–0,93 ms por quadro a 4× (limite 4 ms) |
| N8 | Reconhecimento: o Pedro reconhece o CT e o TR, e as duas armas, a 200 px | **Aprovado pelo Pedro em 2026-10-19**: TR refinado + CT-A com a cabeça ajustada (as armas leem a 200 px: AK e M4A4) |
| N9 | Navbar do site = Partidas, Jogadores, Prancheta (sem botão de ação); "Explorar partidas" principal na landing | protótipo atualizado; `capturas/botoes-navbar-1440.png` e `-375.png`; aceite refeito (`validacao/saida-aceite-fase2b.txt`): A2, A3, A5, A6, C1, C2 sem falhas |
| N2 | Só o agente sorteado é baixado | medido em 2026-10-19: só `agente-ct.js` (34.377 B) ou só `agente-tr.js` (61.181 B) |
| N3 | Reduzir movimento sem nenhuma animação | 0 animações rodando; agente: 1 quadro desenhado, sem novos (CT e TR); gooey sem filtro |
| N4 | Gooey: repouso sem filtro; filtro só na transição | repouso `none`; 60 ms depois da seta `url(#goo)`; 700 ms depois `none` |
| N5 | Navbar não cobre âncora nem foco | 0 ocorrências (§8) |
| N6 | Sem JS: quadro fixo do CT com o rótulo | quadro fixo do **TR** (o padrão) visível, "Agente TR com fuzil"; o do CT fica `display:none` |
| N7 | Privacidade: nenhum arquivo do repositório mostra o cartão do jogador | o pipeline corta em memória; conferido no fim (só `fonte-agente/`, fora do git, tem o vídeo bruto) |

## 13. Ordem de implementação (fases pequenas, cada uma visível e testável)
1. **V1 · Tokens, fontes e marca.** `tokens.css` com dois temas, fontes hospedadas + fallbacks, CSP + teste (com OK), favicon e wordmark na navbar. *Teste:* A6, A8, A3 numa página; `test_csp` novo.
2. **V2 · Páginas claras.** Navbar flutuante, abas gooey (C1, C2), partida inteira e `jogadores.html` no claro, mapa escuro emoldurado. *Teste:* A1, A2, A3, A5, A9, N4, N5.
3. **V3 · Perfil (C5).** Estado vazio honesto, cards com os textos de `erros.py`, comparação lado a lado, mini-radar. *Teste:* A20 (§19), N5, 375 px.
4. **V4 · Prancheta escura.** Tema escuro, "Reproduzir" quente, pontinhos de status, gooey no painel. *Teste:* A3/A4 no escuro, A26.
5. **V5 · Landing com o agente.** Pipeline no build, sorteio, quadro fixo. *Teste:* A12, N1, N2, N3, N6, N7.
6. **V6 · Pontos.** Laterais, carregamento, imagem de compartilhamento. *Teste:* A2 em 1440, A12.

## 14. Pendências e o que fica para o Code decidir
- **Agentes: decididos e finalizados** (2026-10-19, §6): TR refinado + CT-A, TRV1 de reserva. **Pendência da sessão do projeto:** depois do primeiro deploy, testar o `Content-Encoding` com o `agente-tr.js` e o `agente-ct.js` publicados.
- `test_csp.py` muda com o CSP (§3.3): **autorizado**; a mudança é da sessão do projeto.
- Arquivos do agente no projeto: **decidido** (§6.4).
- A13/A14/A25 sem nova medição: **aceito**; se o Code mudar qualquer cor do canvas, refazer.
- **Pendência da sessão do projeto:** fallback da mono no macOS (Menlo) sem métrica medida. Medir `size-adjust`, `ascent-override` e `descent-override` num Mac (ou aceitar o valor do Windows) e conferir que o CLS continua < 0,1.
- **v2 de design fechada em 2026-10-21** (decisão do Pedro). A implementação é da sessão do projeto, com o plano já aprovado lá.
