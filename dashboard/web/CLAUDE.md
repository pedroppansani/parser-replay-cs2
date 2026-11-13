# dashboard/web/: página, mapa e prancheta

Complementa o `CLAUDE.md` da raiz e não o substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. `metrics/tactics.py` e `metrics/annotations.py` espelham o JS: estas regras
valem lá também.

Antes de mexer no `map_core.js`, no canvas, no Replay (`partida/`) ou na prancheta, leia
`dashboard/web/prancheta/CLAUDE.md` (regras de cor, mapa, canvas e prancheta).

## Página

- Nenhum texto nem estilo novo no `template.html` além da estrutura e dos pontos de injeção:
  rótulo de interface sai do JS da camada, frase de card sai do Python (18, 23)
- Texto do dado em `innerHTML` só por `MapCore.esc()` (o único escape) ou `textContent`;
  as regras do começo do CSS não saem sem `py -3.12 -m scripts.compara_paginas` (37)
- Aviso de régua no JS só de `regua_origem` e dos números do perfil (30)
- O replay navega por TICK; fora da janela exportada, a entrada não é clicável e o motivo vai no
  `title` (8d)
- Páginas abrem como arquivo local, sem CDN nem Google Fonts: Geist e Geist Mono em `fontes/` (copiadas de
  `dashboard/web/fontes/`), no máximo 2 famílias; `gera_fontes`/`mede_fallback` não rodam no build (48)
- CLS 0: o que o JS monta depois não empurra a tela (invisível até montar, `:has(... :empty)` no `v2.css`); fontes
  com `preload` só por HTTP e `font-display: fallback` (48)
- CSS novo da v2 só em `v2.css` (marcador `/*__V2__*/`), comportamento comum em `v2.js`; agente: só o sorteado é
  baixado, sha256 no `agentes.manifesto.json`, `converte_agente` fora do build e dos testes (48)
- Escolhas da nota 44 ("Como ficou na implementação") são deliberadas (coluna Mira com o texto do
  Python, mínimos de `jogadores.html`): não "corrija" de volta (44, 48)
- Navbar: Partidas, Jogadores, Reescrever; a prancheta livre é bloco da landing (56)
- Aba Placar: "Quanto cada round pesou" tem o mesmo eixo X do gráfico de cima (viewBox de 900, pL 32,
  pR 12); a barra é depois menos antes da curva publicada, o decisivo é o do payload, e textos e rótulos
  vêm de `leitura/peso_dos_rounds.py` (19, 18)

- Leitor de comandos (`comandos/leitor.js`): puro (sem DOM, rede nem armazenamento); a frase de cada pergunta sai do Python
  (`scripts/comandos_contexto.py`); palavra desconhecida nunca vira alvo em silêncio; não calcula tempo de corrida (64)
- Plano dos comandos (`comandos/plano.js`): puro; recebe o "mundo" (`PlanoDeComandos.cria(W)`: estado da tática, relógio, peças, textos, biblioteca e tempos) e devolve o plano,
  o tempo real de corrida e a busca da granada real, o mesmo para a prancheta e (depois) o Reescrever. No site vem por arquivo, só quando a aba Comandos abre; a página gerada
  sozinha o traz embutido. O texto das funções não muda sem a prova `scripts/design/prova_plano_dos_comandos.py` (64)

## Calibração do Pedro (não resolva sozinho)

- Paleta dos gráficos (10).
