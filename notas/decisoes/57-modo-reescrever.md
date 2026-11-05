# Decisão 57: O modo Reescrever (R2): entrar, editar as peças, sair

- **ID:** 57
- **Status:** vigente
- **Data:** 2026-11-05
- **Resumo:** O Reescrever é um modo da aba Replay (D1): entra-se pelo cabeçalho do palco, pela barra ou por "Reescrever daqui", a moldura e as duas colunas
  viram o violeta da prancheta (D2), as peças vivas do instante ficam editáveis (arrastar) e "Sair" descarta tudo. O mapa não muda de tamanho nem de lugar.

## Texto

57. **Modo Reescrever (R2)** (design do Iriun em `notas/design/reescrever/`; D1, D2 e D7 do Pedro em 2026-11-04).

- **Entrar:** "Reescrever este round" no cabeçalho do palco (D7; botão de 44 px; o cabeçalho continua com 55 px e o resumo do round encurta com
  reticências, o inteiro no `title`), o mesmo botão na barra de ferramentas do mapa e "Reescrever daqui · 0:55" ao lado do ▶, que só aparece com o Replay
  parado. Todos entram no instante em que o Replay está parado (o quadro gravado imediatamente anterior, como o `instante()` da prancheta). Sair: "Sair" ou Esc;
  trocar de round também sai. **Sair descarta as edições** (guardar edição é uma fase futura).
- **O violeta (D2):** `data-tema="violeta"` só no `#palco` e nas duas colunas, enquanto o modo está ligado; navbar, abas, faixa de rounds e página seguem o
  tema da página; o mapa continua escuro. Nenhum token novo. No Assistir nada muda. Os rótulos vêm do Python (`leitura/reescrever.py` → `PAGINA.reescrever`),
  com a frase fixa "Não é uma previsão..." (a mesma da página de escolha).
- **As colunas:** a da esquerda vira o BANCO das 10 peças (CT e TR, com nome, vida, arma e lugar; a viva se escolhe; a morta antes do instante fica
  onde morreu, "morto às 1:42, antes de 1:21", e não se edita); a da direita vira o PAINEL (a frase fixa, "Sua versão começa em ...", a dica, "Voltar
  ao real"). No computador as colunas têm `contain: size` (rolam por dentro), então a linha do palco não muda de altura e nada abaixo dele se mexe;
  no celular descem para baixo do mapa e podem crescer.
- **Editar:** arrastar a peça viva pelo mapa (o ponteiro ganha do desenho e do arrastar do mapa; a peça fica dentro do mapa); a peça editável é 25% maior;
  a selecionada ganha um anel branco sobre o contorno; no mapa fica o losango onde a "Sua versão" começa e o caminho novo, branco sobre o contorno. Mexida de
  menos de 8 unidades não conta como edição. O real fica parado no instante: ▶, a linha do tempo e a velocidade ficam desligados (tocar a "Sua versão" é o R3).
- **Contraste (3:1, pedido do Pedro):** o pior pixel de cada radar processado, contra o melhor dos dois anéis (halo claro e contorno escuro), é 4,13:1 a 4,16:1
  nos 8 mapas com radar do corpus (`scripts.design.mede_peca_reescrever`, e um teste).
- **Fica para as próximas fases:** "Levar o X até" (teclado) e as setas na peça (R6), o fantasma e "O que mudou" (R3), trocar a granada (R4), as portas do "Por que
  perdeu" e do Perfil (R5), o celular com o alternador Real/Sua versão (R6). O botão "Abrir round na prancheta" continua na barra até o Pedro dizer que sai (o
  design o renomeia para "Reescrever este round"; manter os dois não quebra nenhum teste existente).
- **Teclado e saída (code-review do R2):** no modo, setas, espaço, `[` `]` e os cliques no log e nas marcas não mexem no real (que está parado no instante);
  Esc sai, menos quando ele fecha o popover "?" (o Esc de outro dono não descarta as edições) ou com o foco num campo; trocar de round ou de aba também sai;
  as duas colunas trocam o `aria-label` ("Peças" e "Reescrever este round") e o devolvem ao sair. A dica não promete mover pela lista: o teclado é do R6.
- **O que o Assistir ganha (por desenho do Iriun):** o ▶ passa a morar numa caixa de largura fixa (244 px; 136 px no celular) que reserva o lugar do
  "Reescrever daqui", então a linha do tempo fica cerca de 200 px mais curta no computador (90 px no celular) em TODOS os estados, e o cabeçalho do palco ganha o
  botão (o resumo desce para a linha de baixo no celular). Fora disso o Assistir não muda.
- **Limites conhecidos:** abaixo de 1024 x 600 as colunas não têm `contain: size` (o mapa não se mexe, mas o que está abaixo pode descer); no celular o mapa tem
  `touch-action: none` enquanto o modo está ligado (arrastar a peça não rola a página, e o resto do mapa também não); o nome do jogador é a chave da edição.
- **Teste existente alterado (precisa do OK do Pedro):** `test_replay_limpo_browser.py` lista os botões à vista da barra; entrou "Reescrever este round" (`anot-reescrever`).
