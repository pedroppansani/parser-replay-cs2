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
- Reescrever (`partida/10-reescrever.js`): a peça editada tem uma TRILHA com horário (`[{f, x, y}]`, `f` = quadro de partida): segue o caminho real até partir, anda em linha
  reta na velocidade medida até cada parada, e uma parada que parte no meio da anterior a corta; arrastar é UMA parada em t0. A morte do real depois da partida só existe no
  real (D3). Quem edita sem arrastar usa `window.__reescrever.trilha.define`, que recusa peça morta, horário antes do instante e fora de ordem (58)
- Comandos no Reescrever, sem tela (CR1c): o leitor entende nicks só quando o contexto os traz (sem diferenciar caixa e acento; parcial só com 4 letras ou mais, único e fora do
  vocabulário do leitor e dos nomes de lugar; nick que também é lugar do mapa sempre pergunta); `comandos/real.js` monta o elenco do round e dá o veredito de cada comando:
  começa depois da morte ou jogador já morto = recusado ([Escolher outro jogador], [Corrigir]); termina depois da morte = aplicado, a peça esmaece na hora da morte real;
  antes do instante = o real não muda; "bomba ou round?" só depois do plant. Sem nick no contexto (a prancheta) a leitura é a de sempre (64)
- "Até" é o FIM do `segurar` (CR1d): "segura o meio até 0:45" = fica no meio desde agora (ou desde o fim do comando anterior) até 0:45; "aos 0:45" continua sendo o início. O leitor devolve `quando: {tipo: "agora"}` e `fim: {t_decorrido}`; o plano para a peça no destino até o fim (e o comando seguinte parte dele); `esperar` e `mover` não mudam. "Agora" = marcador do tempo na prancheta, instante no Reescrever (`real.js`: `fim_antes_do_instante`, `termina_depois_da_morte`).

## Calibração do Pedro (não resolva sozinho)

- Paleta dos gráficos (10).
