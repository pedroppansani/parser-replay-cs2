# Decisão 44: Direção visual "Sala de demo"

- **ID:** 44
- **Status:** vigente
- **Data:** 2026-10-08
- **Resumo:** O site passa a ter uma direção visual única: tema escuro, placar no estilo do HUD, paleta revalidada contra o fundo do tema, duas famílias de fonte, radar dessaturado por mapa e marcas com anel duplo. A forma vem do documento de entrega; o comportamento continua sendo o do main.

## Texto

44. **Direção visual "Sala de demo"** (design-A a design-E, 2026-10-08). O documento de entrega
(feito por outro agente, fechado em 2026-10-04) está copiado em
[`notas/design/entrega-sala-de-demo.md`](../design/entrega-sala-de-demo.md), e é essa cópia que vale
dentro do projeto. O protótipo navegável fica em `notas/design/prototipo/` (referência; não entra no
build) e os scripts de medição em `scripts/design/`.

**O que o design decidiu** (§17 do documento):

- **Direção 2, "Sala de demo"**, escolhida pelo Pedro. Tema único, escuro.
- **Validador da paleta** (`metrics/paleta.py`) mede o contraste contra o fundo do tema, e não contra
  o branco. Cada cor é "texto" (4,5:1) ou "marca" (3:1) e é medida só contra os fundos onde aparece.
  Daltonismo sem mudança (ΔE2000 ≥ 8 no pior par). A decisão 10 foi revista (§9.3 do documento).
- **Granadas**: smoke `#d1d9e0`, flash `#f9f5b8`, HE `#ff4da6`, molotov `#d65d00`. Aviso `#ffea3d`,
  erro `#ff6b6b`. A forma de cada granada não muda.
- **Uma cor, um papel.** Cor de lado só para o lado: na identidade do time só a etiqueta "começou
  CT/TR" a usa; tudo o que é por round usa o lado em que o time estava naquele round. Vitória e
  link não têm matiz (`--tinta` com "venceu" e sublinhado).
- **Nome dos lados na FACEIT**: "Time de <nick>", só de exibição, calculado em Python. O
  identificador interno do time não muda.
- **Erro do rating em texto** ("erro típico contra o rating oficial: …"), sem faixa desenhada, com o
  valor vindo do `numeros_citaveis.json`. Barra com intervalo só na página de jogadores.
- **Radar dessaturado por mapa** (`RADAR_AJUSTE` em `map_core.js`, tabela reproduzida por
  `scripts/design/gera_radar_ajuste.py`) e **anel duplo** (contorno escuro 2,5 px + halo claro 1,5 px)
  em toda peça e glifo, em todos os estados. O Pedro aceitou o anel duplo no lugar do critério
  literal "preenchimento × P95 do radar" (leitura do WCAG 1.4.11).
- **Texto no mapa** em px de tela (12,5 px), contorno de 6 px, placa a 88%, camada própria e desvio
  de colisão.
- **Duas famílias de fonte** (Archivo e JetBrains Mono, mono só em número), com fallbacks de
  largura medida (CLS 0,199 → 0,003 na landing).
- Grupos da aba Jogadores fechados por padrão, com a linha de resumo e o estado em `localStorage`
  (leitura e escrita em `try/catch`); números antes da imagem na landing.

**Regras para quem implementa** (o §12 do documento é regra dura):

- O mapa continua em canvas; `desenhaJogador` não ganha save/restore (decisão 33).
- Nenhum texto fixo novo no template (decisões 18 e 23); texto do dado passa por `esc()`; número de
  corpus só do `numeros_citaveis.json` (decisão 37).
- O documento dá a FORMA. Onde ela pedir mudar um comportamento que o projeto já tem (a prancheta no
  tempo, o round inteiro, o "comparar dois" na aba Jogadores), vale o comportamento do main, e o
  conflito vai para o relatório.
- Cada fase só pode mudar a forma e deixa **zero diferença numérica**: `scripts/design/impressao_numeros.py`
  compara a impressão das páginas e do `numeros_citaveis.json` com `notas/design/impressao_antes.txt`
  (a do main antes do design). A contagem de testes fica fora da impressão: cresce a cada teste novo.
- Push só no fim (depois da design-E), para o site no ar não ficar no meio do caminho.
