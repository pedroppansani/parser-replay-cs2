# Decisão 43: O round real é uma camada travada; editar em t troca o real só dali em diante

- **ID:** 43
- **Status:** vigente
- **Data:** 2026-10-05
- **Resumo:** O round aberto do replay é a base real do log (`origem.base_real`). Editar um jogador em t corta o real dele depois de t e ancora o estado real em t. Mover alguém num round é deslocamento na velocidade medida, não teletransporte. "Voltar ao real" anula as operações do usuário numa ação.

## Texto

43. **O round real é uma camada travada; editar em t troca o real só dali em diante** (fase 9,
2026-10-05).

- **Base real.** "Abrir round na prancheta" cria a tática com o caminho real de cada jogador
  (`cria_caminho`, simplificado com 32 u, ver `notas/investigacoes/2026-10-05-round-no-hash.md`),
  a saída na morte (ponto com `fora` e `morte`, campos opcionais novos do ponto de caminho),
  as granadas com horário, arremessador e ligação ao arremesso real, o plant e a função
  estrutural de cada jogador (marcada "do replay"). Tudo isso entra no log sem desfazer, e
  `origem.base_real` guarda o número de ordem da última operação real. O que vem depois é do
  usuário, no mesmo log.
- **Editar em t.** A primeira edição de um jogador em t emite, na mesma ação:
  - a remoção dos pontos reais dele depois de t (`remove_ponto`);
  - uma âncora em t com o estado real naquele horário (posição, andar e direção);
  - a edição.

  Sem a âncora, o trecho entre o último ponto real antes de t e o ponto do usuário mudaria a
  posição e a direção antes de t. Os outros jogadores continuam no real.
- **Mover num round** não é teletransporte, porque o jogador estava em algum lugar de verdade em
  t. Ele sai dali e chega ao novo lugar na velocidade medida da função dele, correndo. Na
  tática que não é de round, arrastar continua como antes.
- **Fantasma.** "Mostrar o que aconteceu" desenha o round real (só a base) no mesmo horário,
  esmaecido com o alfa do rastro (`ALFA_RASTRO`).
- **Voltar ao real.** Anula toda operação do usuário ainda ativa numa ação só, pelo `anula`, e
  refazer devolve tudo.
- **Botão.** "Abrir round na prancheta" SUBSTITUIU "Tática deste instante", na mesma posição
  (resposta do Pedro, 2026-10-05): o instante passa a ser o ponto de partida dentro do round
  inteiro. Os seis testes do instante foram migrados e verificam o mesmo no round aberto, parado
  no instante de onde veio: posições, direção do olhar, quem está vivo, granadas ativas e andar.
  Para isso:
  - o quadro do instante sempre fica como ponto do caminho simplificado, então posição e direção
    ali são as gravadas, sem o erro de 32 u;
  - cada granada leva o voo e o efeito medidos no replay (`voo_s` e `efeito_s`, campos opcionais
    novos da `cria_granada`), então fica ativa nos mesmos quadros;
  - a origem da granada é o arremesso real da biblioteca, ou a soltura gravada pelo export, como
    no instante.

  A prancheta continua aceitando `#instante=` de links antigos.
- **Quem arrasta vê quando o jogador chega** (condição do Pedro para o andar até o ponto). Ao
  soltar, o ponto de chegada mostra "chega 1:31", e a linha de dica diz "Spinx anda até o ponto:
  chega 1:31, 2,4 s depois de agora". Sem isso, como a peça continua no lugar em t, pareceria
  que o arrasto não funcionou. O aviso some na próxima ação (clique, cabeçote ou desfazer).
