# dashboard/web/: página, mapa e prancheta

Complementa o `CLAUDE.md` da raiz e não o substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. `metrics/tactics.py` e `metrics/annotations.py` espelham o JS: estas regras
valem lá também.

## Página

- Nenhum texto nem estilo novo no `template.html` além da estrutura e dos pontos de injeção:
  rótulo de interface sai do JS da camada, frase de card sai do Python (18, 23)
- Texto do dado em `innerHTML` só por `MapCore.esc()` (a única função de escape) ou `textContent`;
  as regras do começo do CSS não saem sem `py -3.12 -m scripts.compara_paginas` (37)
- Aviso de régua montado no JS só a partir de `regua_origem` e dos números que viajam no perfil (30)
- O replay navega por TICK; fora da janela exportada, a entrada não é clicável e o motivo vai no
  `title` (8d)
- Páginas abrem como arquivo local, sem CDN nem Google Fonts: Geist e Geist Mono em `fontes/` (o build
  copia de `dashboard/web/fontes/`), no máximo 2 famílias; `gera_fontes`/`mede_fallback` não rodam no build (48)
- Nada que o JS monte depois do HTML empurra o que já está na tela (CLS 0): o que seria empurrado fica invisível até
  montar (`:has(... :empty)` no `v2.css`); fontes com `preload` só por HTTP e `font-display: fallback` (48)
- CSS novo da v2 só em `v2.css` (marcador `/*__V2__*/`), comportamento comum em `v2.js`; agente: só o sorteado é
  baixado, sha256 no `agentes.manifesto.json`, `converte_agente` fora do build e dos testes (48)
- Escolhas da nota 44 ("Como ficou na implementação") são deliberadas: coluna Mira com o texto do
  Python, mínimos de `jogadores.html`; não "corrija" de volta; a partida tem a navbar desde a v2-4 (44, 48)
- Aba Placar: "Quanto cada round pesou" tem o mesmo eixo X do gráfico de cima (viewBox de 900, pL 32,
  pR 12); a barra é depois menos antes da curva publicada, o decisivo é o do payload, e textos e rótulos
  vêm de `leitura/peso_dos_rounds.py` (19, 18)

## Cor e mapa

- CT azul, TR dourado; cada granada mantém a forma do `nadeGlyph`; uma cor, um papel: cor de lado só
  para o lado (por round, o lado daquele round), destaque só no verde do decisivo, vitória e link
  sem matiz; `--erro` e `--aviso` nunca marcam erro de jogador (44, 46)
- Tema por página (`<html data-tema>`); `tokens.css` tem o bloco claro, o escuro e o comum; o canvas lê só
  `*-mapa` e as granadas, iguais nos dois temas; na partida clara a moldura do mapa é a ilha `data-tema="escuro"` (48)
- Cor nova ou trocada passa por `py -3.12 -m metrics.paleta` contra o fundo onde aparece (texto
  4,5:1, marca 3:1, ΔE2000 ≥ 8 no pior par daltônico); o scatter de clusters segue facetado (10)
- Mapa, peças e granadas em canvas, com UM núcleo (`map_core.js`); `desenhaJogador` não ganha
  save/restore (33)
- θ = −yaw só em `MapCore.anguloDeTela`; o ângulo interpola linear pelo caminho curto
  (`interpolaAngulo`), sem Catmull-Rom (34)
<!-- bloco anotacao-unidade-de-jogo: inicio -->
- Anotação guardada em unidade de jogo, com a impressão da calibração em cada traço; todo
  redimensionamento passa por `reprojetaTudo()`, nunca redesenha do que está pintado; espaço +
  arrastar move o mapa e nunca começa traço (23)
<!-- bloco anotacao-unidade-de-jogo: fim -->

## Prancheta

<!-- bloco prancheta-espelho: inicio -->
- A tática é um LOG DE OPERAÇÕES aplicado na ordem (seq, autor, id); mesclar é a união por id;
  persistência só por `Armazem`; arquivo com formato, versão e calibração (outra é recusada); JS e
  Python chegam ao MESMO estado; versão antiga é migrada em memória sem mudar operação (32)
- Desfazer é só `anula`/`reativa`, do mesmo autor; nunca operação inversa por tipo; vida em PASSOS
  (`dura_passos`); ordem de criação é a do log, sem contador próprio; granada do round liga ao
  arremesso real, nunca por proximidade (32)
- Reprodução é função pura do tempo (`estadoNoTempo`; no relógio, `cenaNoRelogio`): arrastar até t e
  tocar até t dão o mesmo quadro; nada é editável durante ela (35, 42)
- Toca no relógio só a tática com operação do formato 3 ou granada com horário; a só com passos toca
  passo a passo; o significado de uma operação existente não muda (42)
- Granada desenhada é desenho (anel tracejado de tela, carimbo, corpo a 100%): sem horário, fora da
  linha do tempo e do roteiro; só "Converter em granada com horário" a torna evento (45)
- Toda operação que entra de fora (arquivo, tática guardada, sala, ao vivo) passa por `problemaDaOperacao`, espelhada em `metrics/tactics.problemas_da_operacao`: validador único, nunca um segundo (47)
- Operação nova da prancheta exige migração nova (`grupos.tipos_de_operacao()`, conferida contra `OPERACOES` do JS e do
  Python); o log do grupo é o estado inicial, numa linha, seguido das operações; os tetos de uso são do servidor (47)
<!-- bloco prancheta-espelho: fim -->
- A interação é UMA máquina de estados (`ESTADOS`); atalhos num mapa único `ATALHOS`, sem tecla
  repetida (32)
- Ponto atrasado é CALCULADO do log (`atrasosDosPontos`) e nunca guardado; desenha-se em `--aviso` com
  "+N s" e texto equivalente; o contador de operações só aparece em "Detalhes técnicos" aberto (35, 43)
- O round real é base travada (`origem.base_real`); editar um jogador em t corta o real dele depois
  de t e ancora o estado real em t; mover num round anda na velocidade medida; "Voltar ao real" anula
  pelo `anula` (43)
- Grupo só transporta o log, sem mudar operação; quem pode desenhar é o servidor (RLS): na recusa a
  operação sai do log local, sem `anula`; sem grupo nada vai à rede; o link `#sala=` nunca entra sozinho: com nick salvo a aba mostra um botão "Entrar no grupo da <mapa> como <nick>" e só o clique conecta (47)

## Calibração do Pedro (não resolva sozinho)

- Paleta dos gráficos (10).
