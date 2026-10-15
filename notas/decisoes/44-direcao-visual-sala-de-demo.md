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

**Como ficou na implementação** (design-0 a design-E3, 2026-10-08 a 2026-10-12). Onde a forma do documento
não coube no comportamento do main, valeu o comportamento, e fica registrado aqui para a próxima sessão não
"corrigir" de volta:

- **"Time de <nick>"** usa o nick que aparece NA PARTIDA (o roster do payload), não o canônico da regra 25:
  em 16 jogador-partidas da FACEIT os dois diferem (donk666 / donk). Regra: o primeiro em ordem alfabética
  (`casefold`, depois a ordem do código), `metrics.times.nome_do_lado_faceit`.
- **`<title>` único:** quando duas partidas teriam o mesmo título (mesmos lados, placar e mapa em eventos
  diferentes), o evento entra para desempatar (`scripts/build_web_page._evento_se_o_titulo_repete`).
- **Cabeçalho da partida vem pronto do build** (placar, decisor, migalhas), e não do JS: montado depois da
  carga, empurrava a página (CLS 0,756; agora 0,062). Por isso "venceu" e "começou CT/TR" saem do Python.
- **Página da partida sem o topo do site:** em 375×667 ele tiraria o controle de tocar da tela (A1). A barra
  de troca de partida ficou (há teste de comportamento); no celular ela ocupa uma linha só.
- **Coluna "Mira":** a frase do documento ("erro mediano… em graus") não descreve a métrica, que é um
  índice de 0 a 100; vale o texto do Python (`D.dica_mira`).
- **jogadores.html:** a forma é a do §7.3, o método é o da fase 7 (intervalo de 95% por reamostragem das
  partidas, ponto encolhido). Mínimos: taxa com menos de 10 tentativas só como bruto; menos de 3 partidas
  sem faixa, em toda métrica (não só no rating). Os 90% do documento ficaram para trás: o Pedro decidiu, na fase 17
  (2026-10-15), que fica o de 95% da fase 7 (decisão 41), e a legenda "Como ler" da página diz qual é.
- **Prancheta:** o roteiro fica AO LADO da linha do tempo (fase 8), não embaixo. As marcas de ação da linha
  do tempo ficam menores que 44 px (com 44 px elas se sobrepõem e o clique cai na vizinha). "Detalhes
  técnicos" com a contagem de operações não entrou: a auditoria 5.3 tirou o contador da tela (há teste).
  O ponto-chave atrasado em `--aviso` não entrou: a página só guarda o atraso de UMA granada por vez.
- **Acessibilidade da prancheta:** fichas do banco são botões (Enter arma; Enter de novo põe a peça no
  centro do mapa), os marcadores de passo têm nome e o canvas tem um resumo em texto
  (`#pr-mapa-resumo`, quem está onde e as granadas). Não houve teste com um leitor de tela de verdade.
- **Medições:** A11 (texto no mapa) no replay dos 8 mapas com partida e na prancheta dos 10 mapas (tática
  sintética no centro de cada radar); A12 da landing e da partida; A10 no `scripts/design/interacao.py`.
  As referências de captura de cada fase estão em `notas/design/referencias/<fase>/`.
