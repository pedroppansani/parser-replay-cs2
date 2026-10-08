> **Cópia do documento de entrega "Sala de demo".** Daqui em diante é ESTA cópia que vale dentro do
> projeto; sessões futuras não precisam da pasta do Iriun.
>
> - **Origem:** `C:\Users\User\Desktop\TimeIA\Iriun\Sites\Base-Design\projetos\parser-cs2.md`
> - **Copiado em:** 2026-10-08
> - **sha256 do original:** `148085801a1797e5cc65494a39838ad692721e42f31c11bd65b01f3171be8f19`
> - **Protótipo (referência visual):** `notas/design/prototipo/` (não entra no build nem em `docs/`)
> - **Scripts de medição:** `scripts/design/` (adaptados: radares locais, páginas de `docs/`, caminhos
>   relativos à raiz)
> - **Escrito antes das fases 7, 8 e 9.** Onde a forma do documento pedir mudar um comportamento que
>   essas fases criaram, vale o comportamento do main, e o conflito vai para o relatório.

---

# Parser de Replay CS2 — design e documento de entrega para implementação

- **Projeto:** `C:\Users\User\Desktop\Projetos Claude\01 - Parser de Replay CS2` (o `design` só lê; quem implementa é a sessão do projeto)
- **Site no ar:** https://pedroppansani.github.io/parser-replay-cs2/
- **Briefings:** [[Sites/Base-Design/projetos/parser-cs2-briefing|fase 1]] (2026-10-03) e [[Sites/Base-Design/projetos/parser-cs2-briefing-fase2|fase 2]] (2026-10-04)
- **Status:** **fechado em 2026-10-04** (fase 2 + rodada de fechamento com as respostas do Pedro em `Claude outputs/PROMPT-Iriun-design-fechamento.md`). **Direção 2, "Sala de demo"**. Protótipo e este documento prontos para a sessão do projeto; o que depende do projeto está em §18 "Pendências de outras fases".
- **Protótipo navegável:** `Sites/Base-Design/prototipos/parser-cs2/prototipo/index.html` (abre como arquivo local; páginas: `index`, `partida`, `prancheta`, `jogadores`, `estados`)
- **Validação:** `Sites/Base-Design/prototipos/parser-cs2/validacao/` — `paleta_v2.py` (especificação executável do validador novo), `paleta_original_copia.py` (cópia fiel de `metrics/paleta.py`), `aceite.py` (critérios de aceite com Playwright), `interacao.py` (roteiro de interação), `baixa_radares.py` + `gera_radar_ajuste.py` (tabela `RADAR_AJUSTE` por mapa e estados da peça, §4.1; gera `radar_ajuste.json`) + `mede_radar*.py` (medições da rodada do valor único), `mede_texto_mapa.py` (contraste do texto no mapa), `mede_lcp_cls.py` (LCP/CLS); saídas `saida-*.txt` de 2026-10-04. Os radares baixados (asset da Valve) **não** ficam no repositório: o script baixa numa pasta temporária.

> Leitor: outra sessão do Claude Code, no repositório do projeto. Tudo o que é preciso está aqui; o protótipo é referência visual e de comportamento, não código para copiar inteiro (o mapa dele é SVG; no projeto continua canvas).

---

## 1. Histórico curto

- **2026-10-03 · fase 1.** Diagnóstico do site no ar (capturas em `prototipos/parser-cs2/capturas/`), 8 problemas e 3 direções (`direcao-1/2/3.html`).
- **2026-10-04 · fase 2.** Pedro escolheu a direção 2, aprovou o critério novo do validador, as cores de granada e o nome "Time de &lt;nick&gt;" para os lados da FACEIT; decidiu o rodapé "Limites", Cache e Vertigo, abas em 375 px, controle de tocar na dobra e "uma cor, um papel".
- **Observação de leitura (2026-10-04):** o validador saiu de `scripts/valida_paleta.py` e hoje é `metrics/paleta.py` (`py -3.12 -m metrics.paleta`), com o mesmo conteúdo. A árvore de trabalho do projeto está à frente do site no ar (ex.: `--dim` já é `#5f6b79`, o `h1` já é `#titulo-partida`, "em quadra" já virou "faz no mapa"). Este documento mapeia contra a árvore de trabalho lida em 2026-10-04.

---

## 2. Cruzamento com a auditoria (`Claude outputs/AUDITORIA-projeto-cs2.md`, 30/09/2026)

### 2.1 Os 8 problemas do diagnóstico

| # | Problema do diagnóstico (fase 1) | Auditoria | Classificação | Onde é resolvido |
|---|---|---|---|---|
| 1 | `h1` da partida é o slogan; placar "Time A / Time B"; vencedor só por cor | Baixa, "Textos confusos": "o `h1` de toda partida repete o da landing" (só o `h1`) | Confirmação parcial: `h1` confirmado; nome dos lados e vencedor só por cor são descoberta | §7.2 cabeçalho; §10 nomes |
| 2 | Tocar fora da dobra; barra de anotação aberta | Baixa: "Replay abre com a barra de desenho inteira, 3 linhas de ferramentas acima do mapa" | Confirmação (barra); tocar fora da dobra é descoberta | §7.2 Replay; critério A1 |
| 3 | Contraste: `--dim`, `--t` como texto, ficha TR, `--aqua` | Baixa, "Acessibilidade": "`--dim` com contraste 3,1:1"; "eventos futuros a 38% de opacidade (2,4:1)" | Confirmação parcial: `--dim` e eventos futuros confirmados; `--t` texto, ficha TR e `--aqua` são descoberta | §3 tokens; §8 eventos |
| 4 | Cor com dois papéis (laranja = TR = molotov = destaque) | Não citado | Descoberta | §4 papéis |
| 5 | Prancheta: granadas na barra, mapa cortado, Cache/Vertigo, sem linha do tempo | Baixa, "Prancheta": "falta link de volta", "texto de depuração", "o banco não diz qual lado é CT e TR" (outros pontos) | Descoberta (os 4 pontos); os 3 da auditoria entram no escopo | §14 |
| 6 | Alvos < 44 px; abas escondidas em 375 px | Baixa, "Acessibilidade": "abas sem navegação por setas, sem `:focus-visible`" | Descoberta (toque e abas escondidas); setas e foco da auditoria entram no escopo | §8 abas; critério A5 |
| 7 | Landing: imagem ilegível, "hero + 3 cards", cards sem time e com frase de cegueira | Média, item 16: "a landing não mostra o que impressiona" (topo genérico, 52 cards de nicks, GitHub após 4.400 px) | Confirmação (topo e grade); frase do card e ordem FACEIT primeiro são descoberta | §7.1 landing; §10 frase do card |
| 8 | 3 famílias de fonte; mono em parágrafo | Não citado | Descoberta | §5 tipografia; critério A6 |

### 2.2 Achados de design/UX da auditoria que o diagnóstico não cobria

Cada item que entrou no escopo tem a fase de implementação (§13) e o critério de aceite.

| Achado da auditoria | Decisão | Fase (§13) | Critério de aceite |
|---|---|---|---|
| 2. Título "Ancient" em toda partida | Doctype etc. já corrigidos (decisão 37). **Entra** o `<title>` e a descrição por partida (§10) | B1 | todo `docs/match_*.html` tem `<title>` = "&lt;lado A&gt; &lt;pts&gt; × &lt;pts&gt; &lt;lado B&gt; · &lt;mapa&gt; · Parser de Replay CS2"; nenhum `<title>` repetido entre partidas |
| 12. Fallback silencioso (`modo_degradado`) | **Entra** o estado "dado degradado" (número escondido, ▲ + motivo) em todo cartão de métrica | B3 | com `modo_degradado` ligado numa partida de teste, nenhum valor numérico aparece no cartão e o rótulo "degradado" aparece; captura no catálogo de estados |
| Baixa: sem favicon nem Open Graph | **Entra**: favicon SVG inline e `og:title`, `og:description`, `og:image` por página | A (favicon) e C (Open Graph da landing), B1 (Open Graph da partida) | toda página de `docs/` tem `<link rel="icon">` e as três `og:*` não vazias |
| Baixa: coluna "MIRA" sem explicação | **Entra**: cabeçalho "Mira" com `title` e a mesma frase na legenda da tabela (§10) | B3 | o cabeçalho tem `title` e a legenda da tabela contém a frase |
| Baixa: "moveu 12% … abaixo dos 12%" | **Entra**: 1 casa decimal quando os dois arredondados coincidem (`narrative.py`, §10) | B1 | teste de `narrative`: nenhuma frase com o mesmo número arredondado dos dois lados de uma comparação |
| 5. Imagens do README | Já em `assets/readme/`. **Entra**: regerar as capturas do README depois do redesenho (`scripts.capturas_readme`) | B3 (partida) e C (landing) | as 4 imagens do README mostram o tema novo; links do README sem 404 |
| 3. Aba Estilos ilegível (`.ev` com duas funções) | Já corrigido no site. **Entra** como regra: classe de componente não se reaproveita entre abas (`.pc-ev` ≠ `.ev`) | B3 | `grep` no template: `.ev` só na linha do tempo do round; o card de estilo usa `.pc-ev`; captura da aba Estilos legível |
| 4. "Limites: nove partidas" | Já sai do JSON; falta trocar "todas de nível profissional" (§10, pendência em §18) | B1 | o rodapé bate com `corpus.por_origem` do JSON |
| 13. MVP = maior rating, componentes ao lado | Já é a decisão 20. **Entra** o desenho do card (rating + erro em texto, métricas com bruto) | B3 | card do MVP sem barra desenhada em volta do rating; erro vindo do JSON |
| 16. Landing | **Entra** (§7.1) | C | `h1`, botões e os 3 números na dobra de 375×667; LCP < 2,5 s e CLS < 0,1 (§15) |
| Baixa: peso das páginas (~440 KB repetidos) | **Fora**: engenharia de build. O design não acrescenta peso (imagens do protótipo: 6 a 12 KB) | — | — |
| Média 9–11, 14, 15, 17; scripts; Streamlit; testes | **Fora**: métrica, validação e organização do código | — | — |

---

## 3. Tokens (CSS variables)

Fonte única: `prototipo/tokens.css`. No projeto ela vira um bloco injetado (ver §11), e **nenhum** arquivo redefine cor por conta própria. Os contrastes abaixo são a saída do `paleta_v2.py` (§9); "papel" é o único uso permitido.

| Token | Hex | Tipo | Papel | Contraste medido (pior fundo onde aparece) |
|---|---|---|---|---|
| `--fundo` | `#0b0f14` | fundo | página | — |
| `--superficie` | `#121820` | fundo | cards, painéis, barras | — |
| `--superficie-2` | `#1a222d` | fundo | elevado: hover, popover, aviso, linha selecionada | — |
| `--radar` | `#0f141b` | fundo | fundo do canvas do mapa e caixa do glifo de granada | — |
| `--tl-fundo` | `#0e131a` | fundo | linha do tempo (replay e prancheta) e lista de eventos | — |
| `--tinta` | `#e8edf2` | texto | texto principal; também **vitória** e **link** (ver §4) | 13,60:1 |
| `--tinta-2` | `#aab5c1` | texto | texto secundário; perdedor; evento futuro | 7,70:1 |
| `--apagado` | `#8b97a5` | texto | rótulo, referência; também **neutro / amostra pequena** (com padrão) | 5,39:1 |
| `--linha` | `#222b37` | decorativa | divisória (sem requisito) | — |
| `--borda` | `#66758a` | marca | borda de botão, chip, campo, tabela | 3,42:1 |
| `--ct` | `#4a90e8` | marca | lado CT: peça, barra, área | 5,48:1 |
| `--ct-texto` | `#6ea8f2` | texto | lado CT em texto | 6,52:1 |
| `--tr` | `#e0a23a` | marca | lado TR: peça, barra, área | 7,98:1 |
| `--tr-texto` | `#e9b65a` | texto | lado TR em texto | 8,62:1 |
| `--decisivo` | `#2fae7c` | texto e marca | round decisivo e rótulo afirmado ("o que decidiu") | 5,70:1 |
| `--smoke` | `#d1d9e0` | marca | smoke (nuvem de três arcos) | 12,95:1 |
| `--flash` | `#f9f5b8` | marca | flash (estrela de quatro pontas com núcleo) | 16,53:1 |
| `--he` | `#ff4da6` | marca | HE (anel serrilhado vazado) | 6,04:1 |
| `--molotov` | `#d65d00` | marca | molotov (gota) | 4,77:1 |
| `--aviso` | `#ffea3d` | texto e marca | aviso ("chega 2,3 s atrasado", dado degradado), sempre com ▲ | 13,04:1 |
| `--erro` | `#ff6b6b` | texto | erro de carga/arquivo, sempre com ✕ e "Erro:" | 5,77:1 |
| `--foco` | `#ffffff` | marca | anel de foco e seleção no mapa | 16,02:1 |
| `--contorno` | `#05080b` | contorno | contorno de peça e glifo no radar | — |

Derivados (só área, nunca texto): `--ct-area rgba(74,144,232,.22)`, `--tr-area rgba(224,162,58,.22)`, `--decisivo-area rgba(47,174,124,.16)`, `--aviso-area rgba(255,234,61,.10)`, `--erro-area rgba(255,107,107,.10)`. Aliases: `--vitoria: var(--tinta)`, `--link: var(--tinta)`, `--neutro: var(--apagado)`.

Texto escuro sobre cor sólida (ficha de jogador, botão principal, "venceu" invertido): `--fundo` sobre `--ct` 5,90:1, sobre `--tr` 8,60:1, sobre `--decisivo` 6,83:1, sobre `--tinta` 16,32:1. **Ficha TR leva texto escuro, nunca branco** (hoje é branco a 3,20:1).

Tipografia, espaço, raio, sombra, movimento (de `Sistema-Base.md`, com o que o projeto ajusta):

```css
/* fallbacks com a largura medida da Archivo: a troca de fonte (display=swap) não muda o número de linhas (CLS) */
@font-face { font-family: "Archivo Fallback"; src: local("Arial"), local("Helvetica"), local("Liberation Sans"); size-adjust: 97.3%; }
@font-face { font-family: "Archivo Cond Fallback"; src: local("Arial Bold"), local("Arial"), local("Helvetica"), local("Liberation Sans"); size-adjust: 77.4%; }
--f-texto: "Archivo", "Archivo Fallback", system-ui, -apple-system, "Segoe UI", sans-serif;
--f-cond: "Archivo", "Archivo Cond Fallback", "Archivo Fallback", sans-serif;   /* onde a Archivo usa largura 75% */
--f-num: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
--larg-condensada: 75%; --larg-normal: 100%;          /* eixo wdth da Archivo */
--t-xs: .75rem; --t-sm: .875rem; --t-base: 1rem; --t-lg: 1.25rem; --t-xl: 1.563rem; --t-2xl: 1.953rem; --t-3xl: 2.441rem;
--t-placar: clamp(1.5rem, 6vw, 2.75rem); --t-relogio: 1.75rem;
--peso-texto: 400; --peso-medio: 600; --peso-forte: 700;
--s-1: 4px; --s-2: 8px; --s-3: 12px; --s-4: 16px; --s-6: 24px; --s-8: 32px; --s-12: 48px;
--r-sm: 3px; --r-md: 4px; --r-full: 9999px;          /* cantos retos: só peça e ficha são redondas */
--sombra-pop: 0 8px 24px rgba(0,0,0,.5);              /* só popover e dica flutuante */
--toque: 44px; --dur: 120ms;                          /* 0ms com prefers-reduced-motion */
```

Estados (comuns a todo controle): hover = `--superficie-2` + borda `--tinta-2`; foco = `outline: 2px solid var(--foco); outline-offset: 2px` (só `:focus-visible`); ligado/selecionado = fundo `--tinta` e texto `--fundo` (botão de ícone e chip) ou sublinhado de 3 px `--tinta` (aba); desativado = opacidade .45 + `cursor: not-allowed` + motivo no `title` ou em texto ao lado.

### 3.1 Tabela "variável atual → token novo"

> **Feita contra os arquivos lidos em 2026-10-04.** As fases 4 e 5 do projeto podem ter mexido neles. **Antes de implementar, a sessão do projeto refaz a conferência** e atualiza números de linha e valores. Busca (ferramenta Grep do Claude Code, ou `rg` na raiz do projeto):
>
> - variáveis CSS: Grep `pattern: "--[a-z0-9-]+\s*:"`, `path: dashboard/web/`, `glob: "*.{html,css,js}"` (e o mesmo em `scripts/build_site.py`) — equivalente: `rg -n -- "--[a-z0-9-]+\s*:" dashboard/web --glob "*.{html,css,js}" --glob "!match_*.html"` e `rg -n -- "--[a-z0-9-]+\s*:" scripts/build_site.py`;
> - usos: Grep `pattern: "var\(--(paper|card|ink|dim|line|ct|t|aqua|dec|mono|display|body)[-)]"` em `dashboard/web/`;
> - hex e rgba fixos: Grep `pattern: "#[0-9a-fA-F]{3,6}\b|rgba?\("` em `dashboard/web/` (sem `match_*.html`, que são saída) e em `dashboard/web/map_core.js`;
> - objeto de cores no JS: Grep `pattern: "var C = \{"` em `template.html`.
>
> Qualquer variável ou hex que apareça e não esteja nas tabelas abaixo segue a regra de §4 (um papel por cor) e entra na conferência.

**`dashboard/web/template.html` (`:root`, linhas 16–51 na árvore de 2026-10-04)**

| Atual | Valor | Token novo | Observação |
|---|---|---|---|
| `--paper` | `#eef1f5` | `--fundo` | |
| `--paper-2` | `#e7ebf1` | `--superficie-2` | |
| `--card` | `#ffffff` | `--superficie` | |
| `--ink` | `#0f1620` | `--tinta` | onde era fundo escuro (tooltip, `pre`), vira `--superficie-2` |
| `--ink-2` | `#4c5a6b` | `--tinta-2` | |
| `--dim` | `#5f6b79` | `--apagado` | |
| `--line` / `--line-2` | `#dde3eb` / `#eaeef3` | `--linha` (divisória) ou `--borda` (controle) | as duas viram uma só divisória |
| `--ct` | `#2a78d6` | `--ct` (marca) / `--ct-texto` (texto) | separar por uso |
| `--t` | `#eb6834` | `--tr` / `--tr-texto` **só quando é lado TR**; ver usos de destaque abaixo | |
| `--aqua` | `#1baf7a` | removido | ver usos abaixo |
| `--dec` | `#0b6b4a` | `--decisivo` (`#2fae7c`) | |
| `--ct-soft` / `--t-soft` | rgba .10 | `--ct-area` / `--tr-area` | |
| `--display` / `--body` | Bricolage / Figtree | `--f-texto` (Archivo) | `--display` vira Archivo com `font-stretch: 75%` |
| `--mono` | DM Mono | `--f-num` (JetBrains Mono) | só número (§5) |
| `--shadow-1` | | removido (borda `--linha`) | |
| `--shadow-2` | | `--sombra-pop` | |
| `--r` | `10px` | `--r-md` (4px) / `--r-sm` (3px) | |

**Usos de `--t` e `--aqua` que NÃO são lado (template.html):**

| Linha (árvore 2026-10-04) | Uso | Novo |
|---|---|---|
| 509 `.autopsy .moment .mt em`, 680 `.decisive .stamp .k`, 755 `.spectacle .comp b` | destaque | `--decisivo` |
| 739 `.card.destaque .tagneg` | rótulo de destaque negativo | `--tinta-2` + `.tag` neutra (decisão 20a: rótulo, não alarme) |
| 773 `.tag.hot` | destaque | `.tag.decisivo` |
| 868 `.pftracos .traco.abaixo b`, 883, 895 | "abaixo da régua" | `--tinta-2` + seta ▼ (forma, não cor) |
| 578 `.clock.armed b` | relógio da bomba | `--tr-texto` (é a bomba do TR), sem piscar (`steps` só sem `prefers-reduced-motion`) |
| 640 `.ev.defuse .who` (aqua) | defuse | `--ct-texto` (é ação do CT) |
| 780 `.fig.piano .role`, 937 `.pc .role.manual` (aqua) | rótulo afirmado / IGL manual | `.tag.decisivo` / `.tag` neutra com "manual" |
| 2101 `C.aqua` (canvas), 2450 `ring(..., C.t : C.aqua)` | anel do destaque | positivo `--decisivo`; negativo `--tinta-2` com ▼ |
| 1234 objeto `C = {ct, t, dec, aqua, ink, …}` | cores duplicadas no JS | ler de `getComputedStyle(document.documentElement)` (uma fonte) |

**Hex fixos no template:**

| Linha | Valor | Novo |
|---|---|---|
| 76–78 `body` gradientes | radiais azul/laranja | removidos: `background: var(--fundo)` |
| 135 `.howto pre` | `#e6edf5` em `--ink` | `--tinta` em `--superficie-2` |
| 151–168 `.rtip` | `#eef2f7`, `#8d9bab`, `#a9b6c4`, `#7fb3f0` | popover: fundo `--superficie-2`, texto `--tinta`, secundário `--tinta-2`, "ir para o round" `--link` sublinhado |
| 182 `.levelpick button.on` | `--ct` + `#fff` | `--tinta` + `--fundo` (andar não é lado) |
| 254 `.teamcard.won` | tom de CT | removido (o placar novo diz "venceu") |
| 267 `.tabs` fundo | gradiente claro | `--fundo` |
| 362 `.rchip.key` | borda laranja | losango `--decisivo` no canto (forma + cor) |
| 385 `.board canvas` | `#161d26` | `--radar` |
| 418–419 `.plr.blind` | amarelo `rgba(232,181,58,.13)` / `#a07a12` | glifo de flash + "cego 2,0 s" em `--tinta-2`, fundo `--superficie-2` |
| 442–445 `.sw.smoke/fire/he/flash` | `#b6c2d0`, laranja, `#d1495b`, `#e8b53a` | glifo SVG real de cada granada (§8), cores `--smoke/--molotov/--he/--flash` |
| 644–645 `.ev.util.flash/he` | inset `#e8b53a` / `#d1495b` | glifo da granada no começo da linha |
| 665 `.decisive` gradiente laranja | | borda superior 2 px `--decisivo` |
| 678 `rgba(255,255,255,.5)` | | `--superficie-2` |
| 954 borda laranja | | `--borda` |
| 1333 `p.fillStyle = "#161d26"` | | `--radar` |
| 2035 `#fff6dc` (flash no canvas) | | `--flash` |
| 2045 `rgba(14,20,27,.85)` | | `--contorno` |
| 2383, 2510, 2577, 2612, 2730 `#e7ebf1` / `#cfd7e1` | grades de gráfico | `--linha` / `--borda` |
| 2504–2639 `rgba(42,120,214,…)` / `rgba(235,104,52,…)` | áreas de lado | `--ct-area` / `--tr-area` |
| 2556–2699 `stroke: "#fff"` | contorno das bolinhas | `--superficie` |
| 2789 `#c9d3de` | barra sem KAST | `--borda` |

**`dashboard/web/tactics.css` (`:root` próprio, linha 7)**: apagar o bloco inteiro (ele repete `--paper … --r` e ainda tem `--dim #7d8a99` e `--alerta #9a5b00`); usar os tokens injetados. `--alerta` → `--aviso`. `.palco` `#161d26` → `--radar`. `.pr-dica-estado` `#0f1620/#e8edf3/#2a3440` → `--superficie-2/--tinta/--linha`. `input … background:#fff` → `--fundo`. `.pr-ajuda` sombra → `--sombra-pop`. `.ativo` → regra de "ligado" acima. `.pr-ficha.t` texto `#fff` → `--fundo`.

**`dashboard/web/annotations.css`**: `.anot-b.on` `#fff` → `--fundo` sobre `--tinta`; bolinha de cor `border:#fff` + anel `--ink` → `--fundo` + anel `--tinta`; sombras `rgba(15,22,32,…)` → `--sombra-pop`; tela cheia `#0f1620` → `--fundo`; `.roundhead` `#eef1f5` → `--tinta`; `rgba(15,22,32,.86)` → `--superficie-2`. O comentário sobre `.board canvas` (fundo transparente com `!important`) continua valendo.

**`dashboard/web/map_core.js`**: `NADE_COLOR` (linha 60) → `{ smoke: "#d1d9e0", molotov: "#d65d00", he: "#ff4da6", flash: "#f9f5b8", decoy: "#8b97a5" }`, de preferência lidos dos tokens na carga. `desenhaArea` molotov `rgba(235,104,52,…)` → `rgba(214,93,0,…)`; smoke mantém os tons claros (já são `--smoke`). Fonte do canvas `'DM Mono'` → `'JetBrains Mono'`. Linha 580 `#eef2f7` → `--tinta`. **Formas não mudam** (`nadeGlyph` já dá forma própria a cada granada).

**`scripts/build_site.py` (landing, linhas 184–194)**: `:root` próprio → tokens injetados; link de fontes → o novo (§5).

---

## 4. Uma cor, um papel

| Papel | Cor | Como se distingue além da cor |
|---|---|---|
| CT | `--ct` / `--ct-texto` | rótulo "CT"; borda esquerda do lado no placar e nas faixas |
| TR | `--tr` / `--tr-texto` | rótulo "TR"; borda direita no placar |
| Vitória / derrota | sem matiz: vencedor `--tinta` + palavra **"venceu"** em caixa; perdedor `--tinta-2` e peso 400 | a palavra e o peso |
| Link | sem matiz: `--tinta` + sublinhado sempre visível | sublinhado |
| Destaque / decisivo | `--decisivo` | losango (◆) na faixa de rounds e no gráfico; borda superior do card |
| Smoke / flash / HE / molotov | `--smoke` / `--flash` / `--he` / `--molotov` | forma própria (nuvem, estrela, anel serrilhado, gota) em radar, linha do tempo, legenda e painel |
| Aviso | `--aviso` | ▲ + "Aviso"/frase em negrito; ponto preenchido na linha do tempo |
| Erro | `--erro` | ✕ + "Erro:" |
| Neutro / amostra pequena | sem matiz: `--apagado` | borda tracejada + rótulo "neutro" / "amostra pequena" |
| Foco / seleção | `--foco` (branco) | anel; seleção no mapa usa anel cheio, traçar caminho usa anel tracejado |

Onde dois papéis dividem o mesmo valor: **vitória, link e texto** usam `--tinta` (não confundem porque vitória vem com a palavra "venceu" e link vem sublinhado; nenhum dos dois depende da cor). **Neutro e amostra pequena** usam `--apagado` (não confundem porque cada um tem o seu rótulo escrito). **Foco e seleção** usam `--foco` (os dois dizem "este é o ativo"; no mapa o foco de teclado é o mesmo anel).

**Cor de lado só para o lado** (decisão do Pedro, 2026-10-04):

- **Identidade do time** (placar e tabelas): nome por extenso + etiqueta pequena "começou CT" / "começou TR". **Só a etiqueta** usa a cor do lado; o placar não tem borda colorida e as linhas da tabela não têm marca colorida.
- **Tudo o que é por round** (replay, faixa de rounds, peças no mapa, eventos, bolinhas do gráfico do Placar): a cor do lado em que o time estava **naquele round**.
- Na comparação de jogadores do corpus, os jogadores se distinguem por **letra (A, B, C) e tom de cinza**, nunca por cor de lado.

### 4.1 Radar dessaturado, por mapa (decisão do Pedro, 2026-10-04)

**Por quê:** o radar oficial (asset da Valve) tem caixas laranja e verdes e pisos coloridos que disputam com TR, decisivo, molotov e HE. Depois do anel duplo (abaixo), o processamento do radar só existe para resolver o **dE**; por isso o par (saturação, brilho) é **por mapa**: um valor único (0,40/0,70, rodada anterior) escurecia sem necessidade mapas que já passavam, e o Inferno caía para 1,27:1 contra o fundo.

**Processamento** (a fórmula não muda): `L = 0,2126 R + 0,7152 G + 0,0722 B` (valores sRGB 0–255, por pixel); `saída = clamp(b × (L + s × (cor − L)))`; alfa intacto.

**Regra de escolha** (por radar; os andares de um mapa usam **um par só**, o pior dos andares, para não mudarem de tom na troca): varrer `b` de 1,00 a 0,50 e `s` de 1,00 a 0,00, em passos de 0,05; pegar o **maior b** e, dentro dele, a **maior s** com dE2000 ≥ 8,0 (pior das três visões: normal, protanopia, deuteranopia) entre as cores dominantes do radar (caixas de 16 níveis com ≥ 1% dos pixels + marcadores coloridos do asset) e TR, decisivo, molotov e HE. Sem par com b ≥ 0,50, o mapa não entra e a decisão volta para o Pedro. Amostra de até 120.000 pixels por andar, semente fixa 28.

**Tabela medida** (`validacao/gera_radar_ajuste.py`, saída em `saida-radar-ajuste-2026-10-04.txt`; os 10 mapas da prancheta, 13 radares, todos baixados do site no ar; todos passaram com b ≥ 0,70):

| Mapa | andar | par (s, b) | pior dE: original → par | piso × fundo do radar: original → 0,40/0,70 → par | anel duplo, pior pixel (par) |
|---|---|---|---|---|---|
| ancient | 0 | **0,65 · 1,00** | 3,4 → 8,2 | 2,38 → 1,60 → 2,34 | 4,13 |
| anubis | 0 | **0,10 · 0,80** | 2,7 → 8,2 | 5,32 → 2,87 → 3,49 | 4,13 |
| cache | 0 | **0,95 · 0,80** | 1,5 → 8,3 | 5,54 → 3,05 → 3,75 | 4,13 |
| dust2 | 0 | **0,90 · 1,00** | 7,3 → 8,1 | 2,34 → 1,60 → 2,35 | 4,13 |
| inferno | 0 | **1,00 · 1,00** (sem mudança) | 15,4 → 15,4 | 1,65 → 1,27 → 1,65 | 4,14 |
| mirage | 0 | **1,00 · 1,00** (sem mudança) | 8,2 → 8,2 | 2,07 → 1,47 → 2,07 | 4,13 |
| nuke | 0 | **0,45 · 0,70** | 1,4 → 8,2 | 5,61 → 3,08 → 3,08 | 4,13 |
| nuke | 1 | (mesmo par) | 0,5 → 11,4 | 5,91 → 3,18 → 3,18 | 4,13 |
| overpass | 0 | **0,80 · 0,85** | 2,4 → 8,2 | 4,14 → 2,41 → 3,17 | 4,13 |
| train | 0 | **1,00 · 1,00** (sem mudança) | 8,0 → 8,0 | 3,03 → 1,91 → 3,03 | 4,13 |
| train | 1 | (mesmo par) | 8,0 → 8,0 | 2,76 → 1,79 → 2,76 | 4,13 |
| vertigo | 0 | **0,65 · 1,00** | 6,2 → 10,5 | 2,75 → 1,77 → 2,72 | 4,13 |
| vertigo | 1 | (mesmo par) | 6,4 → 8,4 | 1,43 → 1,15 → 1,39 | 4,13 |

Observações: Train passa no original no limite (dE 8,0); Nuke continua com o brilho mais baixo (0,70) porque o andar 0 é o mais claro do corpus; Vertigo andar 1 já era escuro no original (1,43:1) e o par quase não mexe nele.

**Constante no topo do `map_core.js`** (com a origem no comentário: esta seção e o `gera_radar_ajuste.py`):

```js
// Dessaturação do radar por mapa: [saturação, brilho]. Gerado por gera_radar_ajuste.py (design, 2026-10-04):
// maior brilho e, dentro dele, maior saturação com dE2000 >= 8 contra TR, decisivo, molotov e HE; passos de 0,05; brilho >= 0,50.
var RADAR_AJUSTE = { ancient: [0.65, 1.0], anubis: [0.10, 0.80], cache: [0.95, 0.80], dust2: [0.90, 1.0], inferno: [1.0, 1.0],
                     mirage: [1.0, 1.0], nuke: [0.45, 0.70], overpass: [0.80, 0.85], train: [1.0, 1.0], vertigo: [0.65, 1.0] };
// Mapa sem entrada: o par mais conservador da tabela (menor saturação e menor brilho) -- e o build avisa.
var RADAR_AJUSTE_PADRAO = [0.10, 0.70];
```

**As condições, na implementação:**

1. **Uma função só, no `map_core.js`:** `MapCore.radarProcessado(imagem, mapa)` devolve um canvas; replay e prancheta chamam a mesma (decisão 33). O mapa é a chave da tabela (`de_` removido: `de_dust2` → `dust2`).
2. **Uma vez, na carga:** desenha o radar num canvas fora da tela, aplica a fórmula por pixel (`getImageData`/`putImageData`) com o par do mapa, guarda e reaproveita com `drawImage`. **Nada de `ctx.filter` por quadro.** Os dois andares do mesmo mapa usam o mesmo par.
3. **Mapa sem entrada:** usa `RADAR_AJUSTE_PADRAO` e o **build imprime um aviso** com o nome do mapa ("radar de &lt;mapa&gt; sem entrada em RADAR_AJUSTE; usando o par padrão 0,10/0,70; rode gera_radar_ajuste.py"). **Teste:** todo mapa com radar no build (`assets/radars/`) tem entrada em `RADAR_AJUSTE`, ou o aviso aparece na saída do build.
4. **Os valores vieram da medição e são reprodutíveis:** `py -3.12 -B baixa_radares.py <pasta>` (ou os PNG de `assets/radars/`) e `py -3.12 -B gera_radar_ajuste.py <pasta>`; a saída tem de bater com a tabela acima e com a constante. **Este script é o critério de aceite da fase B2b.**
5. **Capturas de referência:** as referências do `compara_capturas` são regeradas **num commit próprio**, com a mensagem **"dessaturação do radar por mapa (tabela RADAR_AJUSTE em map_core.js)"**, sem nenhuma outra mudança visual no mesmo commit.

**Marcas: anel duplo, aceito pelo Pedro (2026-10-04).** O critério literal "preenchimento da marca × P95 do radar" só passava apagando o mapa; o Pedro aceitou o anel duplo como a leitura correta do WCAG 1.4.11 (o objeto se separa do vizinho pela borda). Toda peça e todo glifo de granada no mapa levam contorno escuro `--contorno` (2,5 px) **e** halo claro `--tinta` (1,5 px por fora). Em qualquer pixel do radar, um dos dois contrasta ≥ 3:1 (o escuro passa quando o pixel tem luminância ≥ 0,108; o claro, quando ≤ 0,247; as faixas se cobrem). Pior pixel medido nos 13 radares com o par do mapa: **4,13:1**.

**O anel vale em todos os estados da peça** (medido com o par de cada mapa, `gera_radar_ajuste.py`). Só com a cor do lado, cada estado chega a **1,00–1,84:1** em algum pixel de todo radar (é inevitável: todo radar tem pixel da mesma luminância da cor do lado); com o anel duplo, **4,13:1**:

| Estado | Só a cor do lado: pior pixel, nos 13 radares | Com o anel duplo |
|---|---|---|
| Fantasma do round real (tracejado, sem preenchimento) | CT 1,00–1,26 · TR 1,00–1,84 | **halo claro e contorno escuro também tracejados**, mesmo passo do tracejado (5/4): 4,13 |
| Morta (✕ a 60%) | CT 1,00–1,12 · TR 1,00–1,40 | ✕ com halo claro (8 px) e contorno escuro (5,5 px) inteiros por baixo; só o traço colorido fica a 60%: 4,13 |
| Outro andar (anel vazado e ▲/▼ a 50%) | CT 1,00–1,10 · TR 1,00–1,32 | anel vazado sobre o anel duplo inteiro; a seta ▲/▼ com o mesmo contorno escuro: 4,13 |

### 4.2 Texto desenhado no mapa

Nomes e horários no mapa (canvas no projeto; SVG no protótipo):

- **Tamanho em px de tela**, não em unidade do mapa: 12,5 px, peso 600, branco (horário em JetBrains Mono; atrasado em `--aviso`; fantasma em `--tinta-2` itálico). Hoje o rótulo escala com o mapa e chega a 7 px no celular.
- **Contorno escuro de 6 px** (3 px por fora da letra, `paint-order: stroke`) **e placa** `--contorno` a 88% atrás de cada rótulo (folga de 4 px nas laterais e 3 px em cima e embaixo).
- **Camada própria, por cima de tudo:** nenhuma peça, anel, caminho ou área passa por cima de um rótulo.
- **Colisão:** se a placa de um rótulo encosta em outra, tenta acima, abaixo, mais acima e mais abaixo; se nada couber, o rótulo é escondido (o nome aparece no hover e na seleção; o selecionado tem prioridade na implementação).

Medição em §15 (A11).

---

## 5. Tipografia

- **Famílias: 2.** Archivo (eixo `wdth` 75–100, pesos 400–700, variável) e JetBrains Mono (400 e 600). Saem Bricolage Grotesque, Figtree e DM Mono.
- **URL única** (todas as páginas, landing e prancheta inclusive):
  `https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,400..700&family=JetBrains+Mono:wght@400;600&display=swap`
  com `preconnect` para `fonts.googleapis.com` e `fonts.gstatic.com` (crossorigin).
- **Pesos usados:** Archivo 400 (texto), 600 (nomes, valores em frase), 700 (títulos, rótulos condensados, botões); JetBrains Mono 400 (números secundários), 600 (placar, relógio, valores principais).
- **JetBrains Mono só em número:** placar, relógio, valores de métrica, brutos ("27 de 36"), colunas numéricas, porcentagens dentro de frase. Nunca em parágrafo, rótulo, nome ou tag (o `aceite.py` falha se achar palavra de 3+ letras em elemento mono).
- **Archivo condensada (75%) em caixa alta** para rótulos (`.rot`), abas, botões, placar e títulos de seção; **Archivo normal** em texto corrido.
- Tamanho mínimo de texto: 12 px (`--t-xs`). Hoje há 9,5 a 10,5 px em vários rótulos: sobem para 12.

---

## 6. Espaço, raios e sombras

Base 4 px do `Sistema-Base.md`. Gutter de página 16 px; largura máxima 1280 px. Cards com 16 px de padding, borda `--linha` e borda superior de 2 px `--borda` (`--decisivo` no card do round decisivo). Raios 3–4 px (cantos retos do visual "sala de demo"); redondo só peça e ficha. Sombra só em popover e dica flutuante; o resto se separa por linha.

---

## 7. Estrutura das telas (375 px e 1440 px)

Referência navegável: `prototipo/`. Em toda tela: topo do site com marca e 4 links (Partidas, Jogadores, Prancheta, GitHub); em ≤ 640 px a marca encurta para "CS2" e os links ficam numa linha só com rolagem própria.

### 7.1 Landing (`index.html`; builder `scripts/build_site.py`)

1. **Topo (heroi).** 375: uma coluna — rótulo "Projeto de portfólio · Python e JavaScript · site estático"; `h1` em linguagem comum ("Lê gravações de partidas de Counter-Strike 2 e mostra o que decidiu cada jogo"); frase de apoio; botões "Ver uma partida" (principal), "Prancheta tática", "Código no GitHub ↗" (fantasma). Na dobra de 375×667 aparecem `h1` e os botões. 1440: duas colunas (texto 1,05fr | imagem 0,95fr).
2. **Três números, logo depois do texto** (decisão do Pedro, 2026-10-04: o teste dos 5 segundos depende deles): faixa com 3 células (1 coluna em 375, 3 em ≥ 760), número em mono 34 px, rótulo curto, explicação em uma frase; linha do corpus embaixo.
3. **Imagem do replay, depois dos números:** captura WebP de um round (quadro único; no protótipo, 12 KB), com `width` e `height` declarados e `loading="lazy"` (não empurra o layout e não disputa a carga). Legenda dizendo qual round é. **Ordem no HTML = ordem do celular** (texto, números, imagem); no desktop a imagem vai para a coluna da direita só por CSS (`grid-template-areas: "texto figura" "numeros figura"`).
4. **Grade de partidas.** Título "Partidas" com a contagem; filtros: origem (Profissionais · FACEIT · Todas; padrão Profissionais) e mapa (chips com contagem; em 375 rolam numa linha). Cards: mapa · evento · rounds; as duas linhas de time (nome canônico ou "Time de &lt;nick&gt;"), placar em mono, "venceu" escrito; frase "Decidida no round N · MVP X" ou "Nenhum round decidiu sozinho". Ordem: profissionais primeiro, mais recentes antes. 1 coluna em 375, 2 em ≥ 640, 3 em ≥ 1024. Vazio: "Nenhuma partida com esse filtro" + botão "Mostrar todos os mapas".
5. **Rodapé** com "Como os números são conferidos" e link para o README.

### 7.2 Página da partida (`partida.html`; `template.html`)

**Cabeçalho (todas as abas).** Migalhas numa linha com reticências (Partidas / mapa / evento / N rounds); **`h1` = placar no formato do HUD**: `Falcons 17 [começou TR] × 19 MOUZ [venceu] [começou CT]`, sem borda colorida (a etiqueta "começou" é o único uso da cor de lado na identidade do time); linha "Decidida no **round 24** · MVP **m0NESY**" (ou "Nenhum round decidiu sozinho"). Em 375 cada lado vira coluna (nome em cima, número embaixo) e o nome trunca com reticências e `title`. O seletor de partida atual sai do cabeçalho (vai para "Partidas" nas migalhas e para a landing).

**Abas:** Resumo · Replay · Jogadores · Placar · Perfil · Estilos (Resumo primeiro e aberto por padrão). `role=tablist`, setas ← →, Home/End, `tabindex` móvel, hash na URL (`#replay` abre direto). Em 375 as abas rolam na horizontal; quando sobra aba fora da tela aparecem sombra na borda e um botão "›" de 44 px que rola (decisão adicional 3).

**Resumo.** 1440: grade 2 colunas. Card do round decisivo na largura toda: número do round em mono 56 px `--decisivo`, placar antes, frase (Python), haltere 0–100% com antes → depois, equipamento (bruto), empate com outro round como `neutro` + "Como é calculado"; botão "Ver o round 24 no replay" (vai para a aba Replay naquele round). Card MVP: nome + time + função; **o rating em número grande e, ao lado, em tamanho menor, "erro típico contra o rating oficial: {erro_rating}" + link "método"** — sem faixa desenhada (um ± desenhado seria lido como intervalo de confiança do jogador). `{erro_rating}` vem do `numeros_citaveis.json` (chave definida pela fase 4; é o número da validação "deixa uma partida fora, completa"), nunca escrito no template. Logo abaixo, o 2º maior rating e a frase "a diferença é menor que o erro típico" quando for o caso; métricas com bruto e referência (ADR, KAST "27 de 36", aberturas "5 de 6", clutches com "amostra pequena"). Card "Outro destaque" com o motivo dos neutros. Card "Round mais impressionante" com os pesos à mostra. 375: tudo em uma coluna, na mesma ordem.

**Replay.** Faixa de rounds numa linha (chips 44×44, número em mono, barra inferior na cor do **lado** que venceu o round, losango `--decisivo` no decisivo, separador nos meios-tempos e prorrogações). Quadro do mapa: título "Round 24" + resultado em uma linha; mapa (canvas) com tamanho `min(100%, 640px, 100svh − reserva)` (reserva 340 px em 375, 500 px em ≥ 1024); **barra de tocar logo abaixo do mapa, `position: sticky; bottom: 0`** (tocar 44 px, trilho com marcas de kill/plant, relógio do round em mono com "decorrido" em texto, velocidade); legenda com os glifos reais; ferramentas **embaixo da legenda**: "Desenhar" (recolhe todo o desenho), "Direção", "Abrir round na prancheta", tela cheia, "?" (popover com os atalhos, que hoje são dois parágrafos fixos no template). 1440: times CT e TR à esquerda e à direita do mapa (200 px). 375: times embaixo, um sobre o outro. Linha do tempo do round (eventos como botões de 44 px; evento futuro em `--tinta-2`, nunca opacidade .38).

**Jogadores.** Tabela principal sempre visível, com 1ª coluna fixa (nome; embaixo, o time por extenso + etiqueta "começou CT/TR") e colunas **Rating, ADR, KAST, K, A, M** (o rating primeiro, para caber em 375); cabeçalhos ordenáveis com alvo de 44 px. Grupos recolhíveis (`details`) Utilidade, Trocas, Economia, Situações, **todos fechados por padrão**; **cada grupo fechado mostra na própria linha o destaque** ("Utilidade · mais cegueira imposta: m0NESY, 154 s"; "Economia · sem dado de equipamento nesta partida"; "Situações · ▲ degradado"), para fechado não ser escondido. **Aberto/fechado é lembrado por quem vê** em `localStorage` (chave única da página, ex. `parser-cs2:grupos-jogadores`), com leitura e escrita dentro de `try/catch`: se o armazenamento falhar ou vier vazio (arquivo local, modo privado), a página abre com tudo fechado e funciona igual. "Comparar dois jogadores desta partida": dois `select` e **valores lado a lado com o bruto, sem faixa desenhada** (rating com a frase do erro típico; taxa abaixo de 10 tentativas aparece só como bruto + "amostra pequena"). Nunca gráfico de radar.

**Placar.** Gráfico de diferença de rounds: linha `--tinta-2`, bolinha na cor do lado vencedor de cada round, decisivo como losango `--decisivo`, separadores tracejados nos meios-tempos. Legenda com nomes dos times ("Falcons na frente"), não "Time A". Gráfico de probabilidade: mesma regra.

**Perfil e Estilos.** Estrutura atual mantida; mudam tokens, tipografia e estados (`neutro`, `amostra pequena`, "tendência"). Rótulo afirmado usa `.tag.decisivo`; "tendência" e "sem função dominante" usam `.tag.neutro` (hoje usam o azul de CT).

**Rodapé.** Metodologia e Limites, do `numeros_citaveis.json` (§10).

### 7.3 Página de jogadores (nova; `jogadores.html`)

Título "Jogadores no corpus"; aviso fixo (info) "Esta é a visão do corpus, não de uma partida" com o porquê (decisão 30). Controles: chips de mapa, chips de lado (CT e TR · Só CT · Só TR), até 3 jogadores (pílulas com letra **A, B, C** e tons de cinza, porque a cor já tem dono; ✕ de 44 px para tirar; `select` para adicionar, desativado com "Máximo de 3"). Cards de métrica (2 colunas em ≥ 900, 1 em 375): **barras com intervalo** por jogador (é a única tela com faixa desenhada, porque aqui o intervalo é de verdade), linha tracejada da **média da função** (régua de `metrics/perfil_reference.json`), valor e bruto à direita ("73%" e embaixo "226/309"). **O componente não supõe simetria:** o ponto é desenhado na posição do valor e a faixa de `inferior` a `superior`, quaisquer que sejam (Wilson e encolhimento dão faixas assimétricas; o catálogo de estados mostra um caso, 9/41 com faixa de 13% a 34%). **Mínimos:** taxa com menos de 10 tentativas não vira porcentagem nem barra — aparece o bruto ("3 de 7") com "amostra pequena"; rating com menos de 3 partidas não tem faixa — aparece "1 partida" / "2 partidas", sem barra. Outros estados: carregando (esqueleto do tamanho final), vazio ("Nenhum round desses jogadores com esse filtro").

**Proposta de método, como entrada para a fase 7** (o método final é decidido lá, conciliado com o encolhimento que o prompt da fase 7 já pede e conferido contra a decisão 30):

- **Rating:** reamostragem por partida (cluster: sorteia partidas inteiras do jogador, com reposição), **semente fixa** (decisão 28), **2000 repetições**, intervalo de **90%** pelos percentis 5 e 95.
- **Taxas:** intervalo de **Wilson 90%** sobre o bruto (sucessos / tentativas).
- **Mínimos:** 10 tentativas para taxa; 3 partidas para o intervalo do rating.
- **A conciliar com o encolhimento** na fase 7: se o encolhimento for adotado, o ponto passa a ser o valor encolhido e a faixa a do método escolhido; o componente já desenha qualquer faixa assimétrica.

### 7.4 Prancheta — ver §14 (seção separada para as fases 8 e 9).

---

## 8. Componentes e todos os estados

Catálogo visual: `prototipo/estados.html`.

| Componente | Estados |
|---|---|
| Botão (principal, normal, fantasma, de ícone) | normal, hover, foco, ligado (`aria-pressed`), desativado com motivo |
| Chip de filtro | ligado, desligado, foco, desativado ("sem partidas"); contagem em mono |
| Abas | normal, hover, selecionada (sublinhado 3 px), foco (anel interno), sobra à direita/esquerda (sombra + "›") |
| Placar HUD | vencedor/perdedor, etiqueta "começou CT/TR" (sem borda colorida), nome truncado com `title`, 375 em coluna |
| Rating na partida | número + "erro típico contra o rating oficial: {erro_rating}" + "método"; nunca faixa |
| Cartão de métrica | normal (valor + bruto + referência), amostra pequena, neutro (com motivo), dado degradado (`modo_degradado`, número escondido + ▲), carregando (esqueleto), erro |
| Barra com intervalo (só página de jogadores) | normal, **assimétrica** (ponto fora do meio), abaixo do mínimo (só bruto, sem barra), menos de 3 partidas ("2 partidas", sem barra), sem dado ("—"), referência tracejada |
| Haltere (antes → depois) | normal; empate com outro round (tag neutro) |
| Faixa de rounds | normal, selecionado, decisivo (◆), meio-tempo |
| Controles do replay | pausado, tocando, velocidade (1×, 2×, 0,5×, 0,25×), sem radar calibrado (aviso info, replay desligado) |
| Barra de ferramentas do replay | recolhida, "Desenhar" aberto, popover de atalhos |
| Eventos do round | passado, futuro (`--tinta-2`), atual (fundo `--superficie-2`), foco |
| Grupo recolhível | fechado com o destaque na linha (padrão), aberto, lembrado (localStorage), armazenamento indisponível (abre fechado), vazio, degradado |
| Peça no mapa | normal, selecionada, traçando caminho, fantasma do round real, outro andar (anel vazado ▲/▼), morta (✕ a 60%); toda peça e glifo com **anel duplo** (escuro 2,5 px + claro 1,5 px) |
| Rótulo no mapa | 12,5 px de tela, contorno 6 px, placa a 88%, camada por cima; atrasado (`--aviso`), fantasma (itálico `--tinta-2`), escondido por colisão |
| Glifo de granada | smoke, flash, HE, molotov (e decoy: quadrado vazado), sempre na caixa `--radar` fora do mapa |
| Linha do tempo (prancheta) | régua, cabeçote (foco, arrasto), faixa (normal, selecionada, fantasma), ponto-chave, ponto atrasado, granada com duração, marco, morte |
| Linha de dica | livre, traçando, pincel ativo, granada armada, reproduzindo |
| Aviso | aviso ▲, info i, neutro –, erro ✕ |
| Página | carregando (cabeçalho do build aparece antes; abas com esqueleto; barra de progresso), vazio, erro |

Regra herdada da auditoria (item 3): classe de componente não se reaproveita entre abas (`.ev` da linha do tempo ≠ evidência do card de estilo, que é `.pc-ev`).

---

## 9. Mudança no `metrics/paleta.py` e revisão da decisão 10

### 9.1 Especificação

O validador está em `metrics/paleta.py` (antes `scripts/valida_paleta.py`). Especificação executável: `validacao/paleta_v2.py`. As contas (ΔE2000, Viénot 1999, WCAG) **não mudam**; muda o que é medido:

1. **Fundos medidos** (lidos dos tokens):

   | Token | Hex | Onde aparece |
   |---|---|---|
   | `--fundo` | `#0b0f14` | página |
   | `--superficie` | `#121820` | cards e painéis |
   | `--superficie-2` | `#1a222d` | elevado: hover, aba ativa, popover, aviso |
   | `--radar` | `#0f141b` | canvas do mapa (peças e granadas) |
   | `--tl-fundo` | `#0e131a` | linha do tempo |

2. **Limiares:** 4,5:1 para cor marcada "texto"; 3:1 para "marca" (peça, ícone, barra, borda de controle, anel de foco). Cada cor é medida **só** contra os fundos onde aparece (tabela `PALETA` do `paleta_v2.py`). Texto escuro sobre cor sólida entra como texto (`--fundo` contra `--ct`, `--tr`, `--decisivo`, `--aviso`, `--tinta`).
3. **Daltonismo sem mudança:** ΔE2000 ≥ 8 no pior par, protanopia e deuteranopia, por grupo de cores que aparecem juntas: "gráficos (decisão 10)" = CT, TR, decisivo; "radar e linha do tempo" = CT, TR, decisivo, smoke, flash, HE, molotov, aviso; "estados no painel" = ct-texto, tr-texto, decisivo, aviso, erro.
4. **Smoke e flash** passam a ser medidas contra radar e linha do tempo; deixam de ser "falha esperada".
5. **Pares nomeados** impressos sempre: molotov × TR e molotov × decisivo, nas três visões.
6. A paleta continua **lida do arquivo de estilo** (nunca copiada à mão para o script), agora dos tokens; `main()` devolve 1 se algo falhar, para virar teste.

### 9.2 Saída esperada (critério de aceite: o script do projeto tem de dar exatamente isto)

Rodado em 2026-10-04 com `py -3.12 -B paleta_v2.py ../prototipo/tokens.css` (fora do projeto):

```
tokens lidos de tokens.css: 23
criterios: texto >= 4.5:1 e marca >= 3.0:1 contra os fundos onde a cor aparece; dE daltonico >= 8.0 no pior par de cada grupo
fundos: fundo #0b0f14 (página), superficie #121820 (cards e painéis), superficie-2 #1a222d (elevado: hover, aba ativa, popover, aviso), radar #0f141b (canvas do mapa (peças e granadas)), tl-fundo #0e131a (linha do tempo (replay e prancheta))

== CONTRASTE ==
tinta        #e8edf2  texto >= 4.5  fundo 16.32  superficie 15.14  superficie-2 13.60  radar 15.69  tl-fundo 15.82   PASSA
tinta-2      #aab5c1  texto >= 4.5  fundo  9.23  superficie  8.57  superficie-2  7.70  tl-fundo  8.95   PASSA
apagado      #8b97a5  texto >= 4.5  fundo  6.47  superficie  6.00  superficie-2  5.39  tl-fundo  6.27   PASSA
borda        #66758a  marca >= 3.0  fundo  4.10  superficie  3.80  superficie-2  3.42   PASSA
ct           #4a90e8  marca >= 3.0  fundo  5.90  superficie  5.48  radar  5.67  tl-fundo  5.72   PASSA
ct-texto     #6ea8f2  texto >= 4.5  fundo  7.82  superficie  7.26  superficie-2  6.52   PASSA
tr           #e0a23a  marca >= 3.0  fundo  8.60  superficie  7.98  radar  8.27  tl-fundo  8.34   PASSA
tr-texto     #e9b65a  texto >= 4.5  fundo 10.34  superficie  9.60  superficie-2  8.62   PASSA
decisivo     #2fae7c  texto >= 4.5  fundo  6.83  superficie  6.34  superficie-2  5.70  tl-fundo  6.63   PASSA
smoke        #d1d9e0  marca >= 3.0  radar 12.95  tl-fundo 13.06   PASSA
flash        #f9f5b8  marca >= 3.0  radar 16.53  tl-fundo 16.67   PASSA
he           #ff4da6  marca >= 3.0  radar  6.04  tl-fundo  6.09   PASSA
molotov      #d65d00  marca >= 3.0  radar  4.77  tl-fundo  4.81   PASSA
aviso        #ffea3d  texto >= 4.5  superficie 14.52  superficie-2 13.04  radar 15.04  tl-fundo 15.17   PASSA
erro         #ff6b6b  texto >= 4.5  fundo  6.93  superficie  6.43  superficie-2  5.77   PASSA
foco         #ffffff  marca >= 3.0  fundo 19.22  superficie 17.84  superficie-2 16.02  radar 18.48  tl-fundo 18.64   PASSA
fundo        #0b0f14  texto >= 4.5  ct  5.90  tr  8.60  decisivo  6.83  aviso 15.64  tinta 16.32   PASSA

== DALTONISMO (pior par de cada grupo) ==
graficos (decisao 10)      dE normal  39.4 [tr x decisivo]  dE daltonico  12.3 [tr x decisivo (protanopia)]  PASSA
radar e linha do tempo     dE normal  14.9 [flash x aviso]  dE daltonico  12.3 [tr x molotov (deuteranopia)]  PASSA
estados no painel          dE normal  16.7 [tr-texto x aviso]  dE daltonico  10.1 [tr-texto x erro (deuteranopia)]  PASSA

== PARES NOMEADOS ==
molotov #d65d00 x tr #e0a23a: normal  22.0  protanopia  19.1  deuteranopia  12.3   PASSA
molotov #d65d00 x decisivo #2fae7c: normal  55.4  protanopia  21.4  deuteranopia  18.7   PASSA

RESULTADO: PASSA
```

No projeto a primeira linha dirá o arquivo de onde leu os tokens; o resto tem de ser igual, linha a linha.

Por que a HE mudou além do pedido: com a HE antiga (`#d1495b`, e também `#e64c7f` da fase 1) o par **decisivo × HE** caía para ΔE 1,9 em daltonismo (verde e rosa-avermelhado colapsam), e os dois aparecem juntos na aba Replay. A busca conjunta de HE e molotov (saída em `validacao/busca_fase2.py`) deu `#ff4da6` e `#d65d00`, com o pior par do grupo do radar em 12,3.

### 9.3 Texto da revisão da decisão 10 (pronto para colar em `notas/decisoes/10-paleta.md`)

> **Revisão de 2026-10-04 — tema escuro e contraste medido contra o fundo do tema.**
>
> **O que mudou.** O site passou a ter um tema único, escuro (direção "Sala de demo", escolha do Pedro). O critério de contraste do `metrics/paleta.py` deixa de ser "contraste no branco ≥ 3:1" e passa a ser contraste contra os fundos do tema onde cada cor aparece: página `#0b0f14`, superfície `#121820`, superfície elevada `#1a222d`, radar `#0f141b` e linha do tempo `#0e131a`. Cor de texto precisa de 4,5:1; cor de marca (peça, ícone, barra, borda de controle, foco) precisa de 3:1. O critério de daltonismo não muda: ΔE2000 ≥ 8 no pior par, protanopia e deuteranopia (Viénot 1999), agora por grupo de cores que aparecem juntas.
>
> **Por quê.** Medir contra o branco só fazia sentido com página branca. No tema escuro o mesmo critério reprovaria o TR dourado (2,23:1 no branco, 8,60:1 no fundo real) e aprovaria cores que somem no fundo escuro. Smoke e flash, que sempre foram desenhadas sobre o radar escuro, eram "falha esperada" no critério antigo; agora são medidas onde aparecem.
>
> **Cada cor tem um papel.** Molotov deixou de ser o laranja do TR (antes os dois eram `#eb6834`, ΔE 0). Destaque e round decisivo usam só o verde do decisivo, nunca a cor de um lado. Vitória, link e neutro não têm matiz próprio: vêm com palavra, sublinhado ou tracejado.
>
> | Cor | Antes (critério: branco) | Depois (critério: fundo do tema) |
> |---|---|---|
> | CT | `#2a78d6` — 4,42:1 no branco | `#4a90e8` marca 5,48–5,90:1; `#6ea8f2` texto 6,52–7,82:1 |
> | TR | `#eb6834` — 3,20:1 no branco | `#e0a23a` marca 7,98–8,60:1; `#e9b65a` texto 8,62–10,34:1 |
> | Decisivo | `#0b6b4a` — 6,53:1 no branco | `#2fae7c` texto 5,70–6,83:1 |
> | Smoke | `#9fb0c2` — "falha esperada" (2,22:1 no branco) | `#d1d9e0` 12,95:1 no radar |
> | Flash | `#e8b53a` — "falha esperada" (1,89:1) | `#f9f5b8` 16,53:1 no radar |
> | HE | `#d1495b` | `#ff4da6` 6,04:1 no radar |
> | Molotov | `#eb6834` (= TR, ΔE 0) | `#d65d00` 4,77:1 no radar; × TR ΔE 12,3, × decisivo ΔE 18,7 (pior visão) |
> | Pior par daltônico, gráficos | 14,5 (TR × decisivo) | 12,3 (TR × decisivo) |
> | Pior par daltônico, radar | não medido (molotov = TR) | 12,3 (TR × molotov) |
>
> A nota antiga sobre o esmeralda ("não clareie o verde sem rodar o script") continua valendo como método: o verde ficou mais claro **porque** o fundo ficou escuro, e o script confirma (6,83:1 no fundo). O aviso de que "nenhuma quarta cor passa no modo escuro" para o scatter de clusters continua de pé: o scatter segue facetado.

---

## 10. Mudanças de dados e textos

| O quê | Onde | Regra / texto | Teste esperado |
|---|---|---|---|
| **Nome dos lados na FACEIT** | Python (`metrics/times.py` ou vizinho; quem monta os nomes canônicos), nunca no template | "Time de &lt;nick&gt;": o nick canônico (regra 25) que vem **primeiro em ordem alfabética, sem diferenciar maiúscula de minúscula** (`str.casefold()`, depois ordem de código), entre os 5 jogadores que **começaram** a partida naquele lado; desempate pelo steamid. Estável (decisão 28) e independente de desempenho. Exemplo: "Time de donk666 venceu Time de apEX por 13–9"; na match_01: "Time de _AmadeuS" × "Time de 9amaterasu9" | mesmo nome em duas execuções; nenhuma página com "Time A" ou "Time B" (o `aceite.py` procura `\bTime [AB]\b`) |
| Exibição do nome do lado | template / builder | mesmo tamanho do nome canônico; em 375 trunca com reticências; `title` com o nome completo; ao lado, a etiqueta "começou CT/TR" (rótulo do JS) | — |
| **Erro do rating na página** | `numeros_citaveis.json` (chave nova, definida pela fase 4) → template | texto "erro típico contra o rating oficial: {erro_rating}" + link "método", ao lado do rating do MVP e na comparação; o valor é o da validação "deixa uma partida fora, completa"; nunca 0,079 fixo | nenhum número de erro do rating escrito no template (teste estrutural da decisão 37) |
| **Rodapé "Limites"** | `scripts/build_web_page.py` linhas 62–63 | trocar "todas de nível profissional e não do autor" por "{profissional} profissionais e {faceit} da FACEIT", de `corpus.por_origem` do `numeros_citaveis.json` | o texto da página bate com o JSON |
| `h1` e `<title>` da partida | build (`#titulo-partida` já existe) | `h1`: placar HUD "Falcons 17 × 19 MOUZ" + "venceu"; `<title>`: "Falcons 17 × 19 MOUZ · Dust II · Parser de Replay CS2"; meta description: "MOUZ venceu a Falcons por 19 a 17 em Dust II (evento). Decidida no round 24." | nenhuma página com o slogan no `h1` |
| Linha do decisor | `scripts/narrative.py` (decisão 18) | "Decidida no round N · MVP X" ou "Nenhum round decidiu sozinho · MVP X" | — |
| Frase do card da landing | `scripts/build_site.py` (`utility_highlight` sai) | a mesma linha do decisor (Python), no lugar de "X impôs Ns de cegueira" | — |
| Ordem da grade da landing | `build_site.py` | profissionais primeiro; dentro, mais recentes antes | — |
| Título e descrição da landing | `build_site.py` linha 182–183 | `<title>` "Parser de Replay CS2 · partidas lidas round a round"; descrição atual ("utility por efeito, crosshair…") troca pela frase do topo | — |
| Rótulos curtos dos 3 números | `numeros_citaveis.py` (`tres_numeros`) | "placares iguais aos oficiais"; "de erro médio no rating"; "de acerto no botão do arremesso" (contexto continua o mesmo) | README e landing iguais |
| Textos fixos dos painéis | `template.html` (eyebrows, `lead` do Replay e dos atalhos) | saem do template (decisão 23): atalhos vão para o popover "?" gerado em `annotations.js`; títulos de seção vêm do JS | teste estrutural de "sem texto no template" |
| Migalhas | template | tirar "parser próprio · awpy + demoparser2" (vai para Metodologia) | — |
| Legenda do Placar | template | "Falcons na frente", "MOUZ na frente" (nomes), não "Time A/B" | `aceite.py` |
| Legenda de granadas | template | glifo SVG real de cada granada, não os caracteres ● ◆ ✷ ✦ | — |
| Coluna "MIRA" | template/JS | cabeçalho "Mira" com `title` "Erro mediano da mira antes do contato, em graus" e a mesma frase na legenda da tabela | — |
| "moveu 12% … abaixo dos 12%" | `narrative.py` | quando os dois valores arredondados coincidem, mostrar 1 casa decimal | — |
| Rótulo do botão no replay | `annotations.js` | "Abrir round na prancheta" (fase 9) | — |
| Favicon e Open Graph | template, tactics.html, builder | favicon SVG inline (duas bolinhas CT e TR no fundo); `og:title`, `og:description`, `og:image` (a captura do README) | — |
| Resumo dos grupos fechados | Python (destaque de cada grupo) → JS | uma linha por grupo: "mais cegueira imposta: X, 154 s"; "mais kills que foram trade: X, 9 de 19"; "sem dado de equipamento nesta partida"; "degradado" | — |
| Prancheta | `tactics.js` | "2 operações · contador 2" sai do painel para "Detalhes técnicos" (`details` fechado); banco com cabeçalhos "TR · time" e "CT · time"; link de volta "De Falcons × MOUZ · round 9" | — |

---

## 11. O que muda em cada arquivo do projeto

- **Novo bloco de tokens** (um arquivo, ex. `dashboard/web/tokens.css`), injetado no build por um marcador `/*__TOKENS__*/` em `template.html`, `tactics.html` e no `<style>` da landing do `build_site.py`, como já se faz com `/*__ANNOTATIONS_CSS__*/`. É dele que o `metrics/paleta.py` lê.
- **`template.html`:** link de fontes; `:root` atual sai (tabela 3.1); cabeçalho novo (placar HUD, decisor); ordem das abas e Resumo selecionado; abas com setas e "›"; layout do Replay (ferramentas abaixo, transporte sticky, tamanho do mapa); Jogadores (ordem das colunas, grupos `details`, comparar); objeto `C` passa a ler os tokens; gráficos com os tokens; tamanhos mínimos de 12 px; alvos de 44 px; sem texto fixo novo (rótulos vêm do JS).
- **`annotations.css` / `annotations.js`:** cores da tabela 3.1; barra recolhida por padrão (já na árvore); ferramentas abaixo da legenda; popover de atalhos.
- **`map_core.js`:** `NADE_COLOR` novo; área do molotov; fonte do canvas (`JetBrains Mono` nos horários, Archivo nos nomes); ler tokens; constantes **`RADAR_AJUSTE`** e **`RADAR_AJUSTE_PADRAO`** no topo e **`radarProcessado(imagem, mapa)`** (uma vez na carga, par por mapa, aviso no build para mapa sem entrada, §4.1); **anel duplo** em peça e glifo e em todos os estados (fantasma tracejado, morta, outro andar); **rótulos** em px de tela, com contorno de 6 px, placa e desvio de colisão (§4.2).
- **`tactics.css` / `tactics.js` / `tactics.html`:** ver §14.
- **`scripts/build_site.py`:** tokens e fontes (com os fallbacks de §3); topo novo na ordem texto → números → imagem; imagem com `width`/`height` e `loading="lazy"`; cards (nomes, venceu, frase); filtros de origem e mapa; ordem.
- **`scripts/build_web_page.py`:** rodapé "Limites"; `<title>`, descrição e Open Graph por partida.
- **`scripts/narrative.py`:** linha do decisor; arredondamento.
- **`metrics/paleta.py`:** §9.
- **Nova página `jogadores.html`** (builder novo) e um agregado do corpus por jogador (dado; método do intervalo na fase 7, §7.3).

## 12. O que NÃO pode mudar

- CT continua azul e TR continua dourado/laranja; cada granada mantém a **forma** do `nadeGlyph`.
- O mapa, as peças e as granadas continuam em **canvas** do `map_core.js` (o SVG do protótipo é só ilustração); `desenhaJogador` não ganha save/restore (decisão 33).
- Páginas abrem como arquivo local; nenhuma dependência de CDN além do Google Fonts; no máximo 2 famílias.
- Nenhum texto fixo no template além da estrutura (decisões 18 e 23); número de corpus só do `numeros_citaveis.json` (decisão 37); texto do dado passa por `esc()`.
- Página da partida só com números dela; régua anônima do corpus; sem seletor de base (decisão 30). A visão agregada fica só na página de jogadores.
- Todo número com bruto e referência; amostra pequena e neutro com tratamento próprio; intervalos como intervalos; nada de gráfico de radar.
- Comportamento da prancheta (log de operações, `anula`/`reativa`, reprodução pura, máquina de estados) — o design só define a forma.
- Testes existentes não mudam sem o Pedro aprovar.

## 13. Ordem de implementação (fases pequenas, cada uma visível e testável)

1. **A · Tokens e fontes.** Arquivo de tokens injetado nas três páginas (com os fallbacks `Archivo Fallback` e `Archivo Cond Fallback`); link de fontes novo; favicon; mapeamento da §3.1 (template, tactics, annotations, builder, `NADE_COLOR`); `metrics/paleta.py` v2. *Visível:* o site inteiro escuro, com a estrutura de hoje. *Teste:* `py -3.12 -m metrics.paleta` igual à §9.2; só 2 famílias carregadas; contraste de texto ≥ 4,5 (`aceite.py` adaptado para `docs/`). *Esperado:* `compara_capturas` acusa diferença em tudo — é a mudança; a referência nova é tirada no fim da fase.
2. **B1 · Cabeçalho e abas da partida.** Placar HUD com "venceu" e etiqueta "começou", decisor, `h1`/`title`/descrição/Open Graph, Resumo primeiro, setas, "›", rodapé "Limites", arredondamento "12% … 12%". *Teste:* nenhuma página com "Time A/B" (depende da regra da FACEIT, que entra nesta fase em Python); abas por teclado; `<title>` único por partida.
3. **B2 · Replay.** Ferramentas abaixo, transporte sticky, tamanho do mapa, popover de atalhos, legenda com glifos, eventos futuros, anel duplo e rótulos do mapa (§4.2). *Teste:* tocar visível sem rolar em 1440×900, 375×667 e 375×812; texto no mapa ≥ 4,5:1 (A11).
4. **B2b · Radar dessaturado por mapa.** `RADAR_AJUSTE` e `MapCore.radarProcessado(imagem, mapa)` (§4.1), usados pelo replay e pela prancheta; anel duplo nos estados fantasma, morta e outro andar. *Teste:* `gera_radar_ajuste.py` sobre os radares do projeto dá a mesma tabela da §4.1 (critério de aceite); todo mapa de `assets/radars/` tem entrada ou o build avisa; desempenho da reprodução igual ao de antes (sem filtro por quadro); **commit próprio** só com a regeração das referências do `compara_capturas`, mensagem "dessaturação do radar por mapa (tabela RADAR_AJUSTE em map_core.js)".
5. **B3 · Resumo e Jogadores.** Card do MVP com o erro em texto (`{erro_rating}` do JSON); estados; tabela reordenada com etiqueta "começou"; grupos fechados com resumo e `localStorage`; comparar dois sem faixa; "MIRA"; `.pc-ev`; `modo_degradado`. *Teste:* toque ≥ 44; mono só em número; página funciona com `localStorage` bloqueado; regerar capturas do README.
6. **C · Landing.** Topo, três números antes da imagem, imagem lazy com `width`/`height`, grade com filtros, frase do card, ordem, Open Graph. *Teste:* `h1` e "Ver uma partida" na dobra de 375×667; sem rolagem horizontal; **LCP < 2,5 s e CLS < 0,1** (Fast 4G, CPU 4×, 375 px).
7. **D · Página de jogadores** (depois da fase 7, que decide o método). Agregado do corpus (dado) e página. *Teste:* aviso de corpus presente; faixa em toda métrica acima do mínimo; abaixo do mínimo, só o bruto; caso assimétrico desenhado certo.

A prancheta fica fora desta ordem (§14).

---

## 14. Prancheta: forma visual para as fases 8 e 9

*(Seção para anexar ao prompt das fases 8 e 9 do projeto. O comportamento já está especificado lá; aqui está só a forma.)* Referência navegável: `prototipo/prancheta.html`.

**Cabeçalho.** "PRANCHETA ·" + `select` do mapa com dois grupos: "Com partidas no corpus" (Ancient, Anubis, Dust II, Inferno, Mirage, Nuke, Overpass, Train) e "Sem partidas no corpus" (Cache, Vertigo, cada um com a indicação no próprio item). Nos mapas sem corpus aparece um aviso info: "Cache não tem partidas no corpus. Dá para montar a tática; 'Buscar arremesso real' e 'Round real' ficam desligados porque não há arremesso nem round gravado deste mapa", e os dois controles ficam desativados com o motivo no `title`. Linha de origem (quando veio do replay): "De Falcons × MOUZ · round 9 a partir de 1:12 · 4v3", com link de volta para a partida. À direita: "Round real: visível/escondido" (botão de alternância).

**Barra de cima (só isto):** Vista (− · zoom · + · tela cheia) | Andar (só nos mapas de dois andares; na Mirage, "Andar único" desativado) | Pincéis (Caneta, Seta, Forma, Texto, Borracha; **cor e espessura aparecem só com um pincel ligado**, separadas por traço) | Desfazer · Refazer | **Reproduzir** (botão principal, à direita; em 375 vira a primeira linha, largura total). Granadas **não** ficam aqui.

**Linha de dica** (logo abaixo da barra, `role=status`, fundo `--superficie-2`): diz o que o próximo clique faz. Textos: livre — "**Clique** num jogador para traçar o caminho · **arraste** para mover · **botão direito** com um jogador selecionado: ele olha para o ponto"; traçando — "**Traçando o caminho de Spinx.** Próximo clique: novo ponto (a hora de chegada aparece nele, a partir de 1:28). Botão direito: Spinx olha para o ponto. Esc termina."; pincel — "**Caneta.** Arraste no mapa para desenhar. Esc volta a mover jogadores."; granada armada — "**Smoke de Brollan.** Próximo clique: onde a granada cai (sai às 1:40)."; reproduzindo — "**Reproduzindo.** Nada é editável agora. Espaço pausa." (os textos saem do `ESTADOS` do `tactics.js`).

**Mapa.** Canvas quadrado, `min(100%, 100svh − 120px)`, fundo `--radar`. Relógio grande no canto superior esquerdo (mono 600, 42 px; 32 px em 375): relógio do round descendo de 1:55; depois do plant, contagem da bomba de 0:40 em `--tr-texto` com "bomba plantada". Avisos empilhados no pé do mapa (em 375, abaixo do mapa): "▲ **Spinx chega 2,3 s atrasado** ao marco 'entrada no A' (1:30). Encurte o caminho ou tire espera de um ponto."

**Radar** já processado por `MapCore.radarProcessado()` (§4.1), o mesmo do replay. **Peças** (canvas, `desenhaJogador`): raio 10 px na escala atual, **anel duplo** (contorno `--contorno` 2,5 px + halo `--tinta` 1,5 px por fora), cunha do olhar escura; nome acima segundo §4.2 (12,5 px de tela, contorno 6 px, placa, camada por cima, desvio de colisão). Estados: normal; **selecionada** (anel `--foco` 3 px, raio 15); **traçando caminho** (anel `--foco` tracejado 5/4); **fantasma do round real** (sem preenchimento, contorno tracejado na cor do lado, nome em itálico `--tinta-2` + "· real"; caminho real pontilhado `--tinta-2`); **outro andar** (anel vazado + ▲/▼, já existe); **morta** (✕ na cor do lado a 60%). Arrasto começa depois de 4 px (`LIMIAR_ARRASTO_PX`). Caminho: tracejado branco 8/5; cada ponto é um círculo branco com o horário de chegada em mono ("1:47"); ponto atrasado em `--aviso` com "+2,3 s".

**Granadas no mapa:** voo como linha pontilhada na cor da granada; ao cair, glifo sobre uma placa redonda `--contorno` com borda `--tinta` 1,5 px (anel duplo) + área (smoke com raio `RAIO_SMOKE_UNIDADES`, molotov com `RAIO_MOLOTOV_UNIDADES`) pelo tempo real de duração.

**Painel da direita (320 px; em 375 vai para baixo do mapa)** com abas Jogadores · Granadas · Tática:
- **Jogadores:** grupos "TR · MOUZ" e "CT · Falcons" (rótulo com o lado escrito, cor do lado); cada linha é botão de 44 px com ficha redonda (iniciais, texto `--fundo` sobre a cor do lado), nome e **função** à direita (entry, trade, suporte, AWP, lurk, âncora…); morto = ficha tracejada + "morre 1:07"; os do round real marcados "· real". Abaixo, **Selecionado**: "Spinx · TR · entry · 3 pontos de caminho · chega ao último às 1:28".
- **Granadas:** quatro botões grandes (56 px) em 2×2 — glifo na caixa `--radar`, nome e atalho (1–4); o ligado ganha anel `--foco`. Depois, "Buscar arremesso real" (largura total) e uma frase do que ele faz. As fichas de arremesso real mantêm o aviso de comando não conferido (decisão 21b) como aviso info.
- **Tática:** nome, autor, Exportar · Importar · Nova, frase "Salva neste navegador…", e "Detalhes técnicos" (`details` fechado) com a contagem de operações.

**Linha do tempo (embaixo do mapa e do painel, largura total, fundo `--tl-fundo`):**
- Topo: relógio atual (mono 28 px) e a dica "Arraste o cabeçote ou use ← → (Shift: 5 s)".
- **Régua:** marcas a cada 10 s com o relógio do round (1:55, 1:45…); a partir do plant, a zona da bomba sombreada em `--tr-area` e os rótulos em `--tr-texto` (0:40, 0:32…). Rótulos regulares a menos de 5 s do plant somem para não encavalar.
- **Marcos nomeados:** losango + nome + horário ("plant 0:40" com losango `--tr`), em duas alturas alternadas para não sobrepor. São rótulos; pular para eles é pelo **roteiro**.
- **Faixa por jogador** (44 px de altura): nome e função fixos à esquerda (132 px; 96 em 375), borda esquerda na cor do lado; barra de vida na cor do lado até a morte (✕); pontos-chave (anel branco 14 px, preenchido em `--aviso` se atrasado); granadas (glifo na caixa escura 26 px, no horário da soltura) com a **duração** listrada na cor da granada (smoke 18 s, molotov 7 s); faixa selecionada com fundo `--superficie-2`; faixas do round real (fantasma) em itálico, borda tracejada e pontos tracejados.
- **Cabeçote:** linha `--foco` de 2 px com triângulo no topo; área de arrasto de 44 px; `role=slider` com `aria-valuetext` = relógio; setas, Shift+setas, Home, End. Clicar em qualquer ponto da grade leva o cabeçote até lá.
- **Roteiro sincronizado** (lista abaixo, linhas-botão de 44 px): "1:40 · Brollan (suporte) · smoke CT · da rampa"; a linha do instante atual fica destacada; clicar leva o cabeçote ao horário.
- Em 375 a grade tem largura mínima de 760 px e rola **dentro** da caixa (a página não rola na horizontal); os nomes ficam fixos à esquerda.

**Reprodução:** relógio grande correndo, peças andando, granadas saindo no horário e caindo, smoke durando o tempo real, roteiro acompanhando; barra de edição e painel ficam a 45% e `inert`; o botão vira "❚❚ Pausar e editar".

**Celular (≤ 640 px), desenhado e não abandonado:** some a parte de desenho e de andar da barra (aviso info: "No celular: ver, tocar e mover jogadores, e granada pela aba Granadas. Desenho à mão e andares só no computador"); Reproduzir em largura total no topo; mapa em largura total; painel em abas embaixo; linha do tempo com rolagem horizontal interna; arrastar peça e cabeçote funciona com toque (pointer events).

---

## 15. Critérios de aceite (verificáveis)

Medidos no protótipo em 2026-10-04 com `validacao/aceite.py` (Chrome via Playwright; saída integral em `validacao/saida-aceite-2026-10-04.txt`). A sessão do projeto roda o mesmo roteiro contra `docs/`.

| # | Critério | Como medir | Protótipo |
|---|---|---|---|
| A1 | Controle de tocar visível sem rolar | `partida.html#replay` e clique na aba Replay; `getBoundingClientRect` do botão dentro da tela e `elementFromPoint` no centro = o botão; `scrollY = 0` | 1440×900: topo 815, base 859 (tela 900) PASSA · 375×667: 615–659 (667) PASSA · 375×812: 760–804 (812) PASSA |
| A2 | Nenhuma rolagem horizontal da página em 375 px | `scrollWidth ≤ 375` em todas as páginas e abas | 375 em todas (10 páginas/abas × 2 alturas) |
| A3 | Todo texto ≥ 4,5:1 (≥ 3:1 se ≥ 24 px ou ≥ 18,66 px negrito) contra o fundo efetivo | varredura de todo nó de texto visível, fundo composto pelos ancestrais | menor razão 5,39:1 (apagado sobre superfície 2); nenhuma falha |
| A4 | Marcas gráficas ≥ 3:1 | `paleta_v2.py` (tokens) + borda de botão/chip/campo no DOM | tokens: todas PASSA (menor 3,42:1, borda sobre superfície 2); DOM: nenhuma borda < 3:1 |
| A5 | Toque ≥ 44×44 | todo `a`, `button`, `select`, `input`, `summary`, `[role=tab]`, `[role=slider]` visível (link dentro de frase fica de fora, WCAG 2.5.8) | nenhuma falha (depois de corrigir marca, "›", chips de round, cabeçalhos de tabela, marcos e cabeçote) |
| A6 | Só 2 famílias de fonte carregadas; mono só em número | `document.fonts` com status `loaded`, sem contar os apelidos locais `… Fallback` (são Arial/Helvetica do sistema, sem download); elementos em JetBrains Mono sem palavra de 3+ letras (o marcador `{erro_rating}` não conta) | Archivo + JetBrains Mono em todas; nenhuma palavra em mono |
| A7 | Nenhuma partida com "Time A / Time B" | `innerText` sem `\bTime [AB]\b` | nenhuma ocorrência |
| A8 | Paleta | `py -3.12 -m metrics.paleta` igual à §9.2 | PASSA (saída acima) |
| A9 | Abas por teclado | foco em Resumo, → vai para Replay e mostra o painel; End vai para Estilos | PASSA (`saida-interacao-2026-10-04.txt`) |
| A10 | Prancheta | clique no mapa traçando acrescenta ponto; clique na linha do tempo move o relógio; Home volta a 1:55; Reproduzir corre o relógio; Cache mostra o aviso e desliga "Buscar arremesso real" | PASSA, sem erro de JS (refeito com os radares por mapa) |
| A11 | Texto desenhado no mapa ≥ 4,5:1 (3:1 se ≥ 18,66 px de altura ou negrito ≥ 14 px) contra o pixel mais claro do fundo local, considerando o contorno | `mede_texto_mapa.py`: três capturas (normal; texto sem preenchimento; sem texto); glifo = onde as duas primeiras diferem; fundo local = pixels a até 2 px da letra, na captura sem preenchimento; mede o mais claro contra a cor declarada do texto; 1440 e 375 px de largura, sobre os radares dessaturados | **antes** (fase 2: rótulo em unidade do mapa, contorno 4, sem placa, radar original): pior 1,00:1, de 3 a 11 rótulos reprovados por tela, 7 a 9 px de altura em 375 · **depois** (refeito com os radares por mapa, Dust II 0,90/1,00 e Mirage 1,00/1,00): pior **9,06:1** (prancheta 1440, "Spinx · real"), 0 reprovados; replay 16,52:1 (1440) e 18,91:1 (375); prancheta 9,13:1 (375) |
| A13 | Radar por mapa: dE ≥ 8,0 com o par da tabela | `gera_radar_ajuste.py` sobre os radares do build | 13 de 13 radares (10 mapas) PASSAM; tabela em §4.1 |
| A14 | Anel duplo em todos os estados (normal, fantasma tracejado, morta, outro andar) ≥ 3:1 no pior pixel de cada radar | `gera_radar_ajuste.py` (pior pixel do maior dos dois anéis, por radar) | 4,13:1 nos 13 radares; só a cor do lado daria 1,00–1,84:1 |
| A15 | Mapa sem entrada na tabela | build com um radar fictício fora de `RADAR_AJUSTE` | usa 0,10/0,70 e o build imprime o aviso com o nome do mapa (teste do projeto; não há build no protótipo) |
| A12 | Desempenho | `mede_lcp_cls.py`: `PerformanceObserver` (`largest-contentful-paint`, `layout-shift`), 375×667, rede Fast 4G (9/1,5 Mbit/s, 165 ms), CPU 4× mais lenta, cache limpo, 5 medidas por página, servido por HTTP local | **landing:** LCP mediana **0,94 s** (pior 0,94), CLS **0,003** (era 0,199 antes dos fallbacks medidos: a troca de fonte reflowava o `h1`) · **partida:** LCP 0,90 s, CLS **0,004** (refeito depois dos radares por mapa) |

**Critérios para o site real (A12):** **landing: LCP < 2,5 s e CLS < 0,1**; **partida: só CLS < 0,1**. O LCP da partida depende dos 2 a 4 MB de dados embutidos (engenharia de build, fora do escopo do design); o protótipo não tem esses dados, então o 0,90 s dele não vale como previsão.

Limites da medição (honestos):
- A11 foi medido no SVG do protótipo; no projeto o texto é canvas. A sessão do projeto repete a medição com o mesmo método sobre capturas do replay e da prancheta (as três capturas saem trocando o preenchimento do texto no `map_core.js` por transparente e depois escondendo o texto).
- No A11 a janela teve 3.200 px de altura (largura real de 1440 e 375) para caber numa captura sem redimensionar a página: a captura de página inteira dispara `resize`, e o desvio de colisão mudava entre as três capturas. O rótulo é em px de tela, então a altura não muda o resultado; o mapa da prancheta fica maior do que em 900 px.
- O "antes" do A11 foi emulado sobre o protótipo atual (radar original, rótulo em unidade do mapa, contorno de 4, sem placa, sem desvio de colisão), com o rótulo já na camada de cima; o antes real era um pouco pior.
- A12 foi servido por HTTP local, com as fontes do Google pela rede limitada; o GitHub Pages tem outra latência.
- O rótulo escondido por colisão não é medido; ele aparece no hover e na seleção.

## 16. Checklist de acessibilidade e mobile (avaliado no protótipo)

- [x] Contraste de texto ≥ 4,5:1 — menor medido 5,39:1.
- [x] Marcas ≥ 3:1 — menor medido 3,42:1 (borda de controle); peças e granadas no radar ≥ 4,77:1.
- [x] Nada só por cor — vitória com "venceu", decisivo com ◆, granadas com forma, aviso com ▲, erro com ✕, neutro e amostra pequena com tracejado e rótulo, lado com rótulo CT/TR.
- [x] Foco visível — anel branco 2 px + 2 px de folga em todo controle (`:focus-visible`).
- [x] Abas com setas, Home e End, `tabindex` móvel; cabeçote com setas e `aria-valuetext`.
- [x] Toque ≥ 44 px em tudo o que é interativo (exceção WCAG: link dentro de frase).
- [x] 375 px sem rolagem horizontal; tabelas e linha do tempo rolam dentro da própria caixa com a 1ª coluna fixa.
- [x] Tocar do replay visível sem rolar em 1440×900, 375×667 e 375×812.
- [x] Abas fora da tela em 375 sinalizadas (sombra + "›").
- [x] `prefers-reduced-motion`: transições a 0 ms, esqueleto sem brilho, relógio da bomba sem piscar.
- [x] Textos alternativos: imagem do topo com `alt`; mapa com `aria-label`; gráficos com `role="img"` e rótulo que diz o dado.
- [x] Fontes: 2 famílias, `display=swap`.
- [x] Texto no mapa ≥ 4,5:1 — menor medido 9,06:1 (A11), com rótulo de 12,5 px de tela, contorno de 6 px e placa.
- [x] Marcas no radar: anel duplo, ≥ 4,13:1 em qualquer pixel dos 13 radares (10 mapas), em todos os estados da peça (§4.1).
- [x] Landing: LCP 0,94 s e CLS 0,003 em Fast 4G com CPU 4× (A12).
- [x] Grupos da aba Jogadores funcionam com `localStorage` bloqueado (leitura e escrita em `try/catch`).
- [ ] A conferir na implementação: A11 no canvas real; leitor de tela na prancheta (as peças hoje não são focáveis no canvas; o protótipo mostra o padrão `role=button` + Enter para selecionar).

---

## 17. Decisões

- 2026-10-03 · Fase 1: diagnóstico, 3 direções, esboços.
- 2026-10-04 · Direção 2 escolhida pelo Pedro. Tema único escuro. Critério do validador: contraste contra o fundo do tema (aprovado). Granadas novas (aprovadas): smoke `#d1d9e0`, flash `#f9f5b8`, HE `#ff4da6`, molotov `#d65d00`. Lados FACEIT: "Time de &lt;nick&gt;" (regra de dado). Rodapé "Limites" corrigido via JSON. Cache e Vertigo num grupo "sem partidas no corpus". Uma cor, um papel.
- 2026-10-04 · Decisões do `design` na fase 2: HE mudou de `#e64c7f` para `#ff4da6` porque decisivo × HE caía para ΔE 1,9; aviso `#ffea3d` e erro `#ff6b6b` escolhidos por busca contra o conjunto do radar; transporte do replay sticky; marcos da linha do tempo como rótulos (pular pelo roteiro). Paleta final e `metrics/paleta.py` aprovados pelo Pedro como entregues.
- 2026-10-04 · **Fechamento (respostas do Pedro):** radar dessaturado aprovado com quatro condições (primeiro medido como valor único s 0,40 / b 0,70, substituído no mesmo dia pela tabela por mapa, abaixo); erro do rating em texto `{erro_rating}`, sem faixa, valor do JSON; barra com intervalo só na página de jogadores, assimétrica, com mínimos (10 tentativas; 3 partidas); métodos como proposta para a fase 7; cor de lado só para o lado (etiqueta "começou CT/TR" na identidade do time); grupos da aba Jogadores fechados, com resumo e `localStorage`; números antes da imagem na landing, imagem lazy com `width`/`height`; texto do mapa em px de tela com contorno, placa, camada própria e colisão; fallbacks de fonte com a largura medida (CLS 0,199 → 0,003).
- 2026-10-04 · **Decisões do Pedro, brilho por mapa:** (1) **anel duplo aceito** no lugar do critério literal "preenchimento × P95", como leitura do WCAG 1.4.11, e obrigatório em todos os estados da peça (fantasma com halo e contorno tracejados, morta, outro andar); (2) **brilho por mapa**, função única com a tabela `RADAR_AJUSTE` (maior brilho e, dentro dele, maior saturação que passam dE ≥ 8,0; passos de 0,05; piso de brilho 0,50; um par por mapa para todos os andares; Cache e Vertigo medidos; mapa sem entrada usa o par mais conservador, 0,10/0,70, e o build avisa). Medido: todos os 10 mapas passaram com brilho ≥ 0,70; Inferno, Mirage e Train ficam sem mudança.

---

## 18. Pendências de outras fases

O que depende do projeto e não do design. Nada disto é feito pelo `design`.

| Pendência | Quem / onde | O que o design entrega para ela |
|---|---|---|
| **Chave do erro do rating** no `numeros_citaveis.json` | fase 4 do projeto (validação "deixa uma partida fora, completa", regra de desempate nova) | o lugar e o texto na página: "erro típico contra o rating oficial: {erro_rating}" (§7.2, §10) |
| **Método final da página de jogadores** (intervalo do rating e das taxas, encolhimento) | fase 7 do projeto, conferido contra a decisão 30 | a proposta (reamostragem por partida com semente fixa, 2000 repetições, 90%; Wilson 90%; mínimos) e o componente que desenha faixa assimétrica (§7.3) |
| **Regra de nome dos lados FACEIT** ("Time de &lt;nick&gt;") | Python, sessão do projeto (regras 25 e 28), fase B1 | a regra, o exemplo e o teste (§10) |
| **Mudança no `metrics/paleta.py` e revisão da decisão 10** | sessão do projeto, fase A | a especificação, a saída esperada e o texto da nota (§9) |
| **Regeração das capturas de referência** do `compara_capturas` por causa da dessaturação do radar | sessão do projeto, fase B2b, em commit próprio | a tabela `RADAR_AJUSTE`, a fórmula, o script `gera_radar_ajuste.py` (critério de aceite) e a mensagem do commit (§4.1) |
| **Aviso no build para mapa sem entrada em `RADAR_AJUSTE`** | sessão do projeto, fase B2b | o texto do aviso, o par padrão e o teste (§4.1) |
| **Rodapé "Limites"** ("43 profissionais e 9 da FACEIT", do JSON) | `scripts/build_web_page.py`, fase B1 | o texto e o teste (§10) |
| Destaque de cada grupo recolhido (linha de resumo) | Python, fase B3 | o formato das quatro linhas (§10) |
| Agregado do corpus por jogador (steamid) | sessão do projeto, antes da fase D | a página e os estados (§7.3) |
