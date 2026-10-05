# Decisão 41: Métricas de impacto no perfil; comparação entre partidas só em jogadores.html

- **ID:** 41
- **Status:** vigente
- **Data:** 2026-10-04
- **Resumo:** Utilidade, trocas e situações entram no perfil (`metrics/impacto.py`); o agregado por jogador vive em `jogadores.html`, por steamid, com encolhimento declarado.

## Texto

41. **Métricas de impacto no perfil; comparação entre partidas só em `jogadores.html`** (fase 7,
2026-10-04).

- **Impacto** (`metrics/impacto.py`): dano por HE e por molotov, inimigos e segundos de cegueira por
  flash, kills em inimigo cego por flash, cegueira nos companheiros (conta contra), tempo mediano da
  troca, pós-plant (TR) e retake (CT) de quem estava vivo no plant, duelos de abertura por lado.
  Entram no perfil (decisão 7a) com bruto, régua do corpus e amostra fraca pelo piso de eventos. As
  contagens que já existiam batem jogador a jogador (kills de troca, aberturas).
- **Na partida**, a comparação é o "Comparar dois" da aba **Jogadores** (resposta 6 do Pedro,
  2026-10-05; o documento de design a põe ali, §7.2 e §8 de `entrega-sala-de-demo.md`). São dois
  jogadores DAQUELA partida, de qualquer time, nas taxas do perfil e nas métricas de impacto, cada
  número com o bruto e a régua anônima do corpus, sem faixa desenhada. A seleção é estado da tela
  (não vai para o endereço), e não o seletor de base que a decisão 30 proíbe. A aba Perfil fica
  como estava antes da fase 7.
- **Entre partidas**, só em `jogadores.html` (o "lugar separado" da decisão 30): por steamid, razão
  das somas, intervalo por bootstrap das partidas (semente fixa) e encolhimento para a média da
  função com peso m / (m + k), k por métrica estimado no corpus (variância dentro / entre jogadores).
  Sem variação entre jogadores (k indefinido), a página diz que o corpus não separa ninguém.
- Rótulos das taxas do perfil em `metrics/player_profile.ROTULOS_DAS_TAXAS`, para as duas páginas.
- **Economia** (7.2.3, resposta 5 do Pedro): rating, ADR e KAST pela compra do time dele e kills
  contra compra cheia e em anti-eco. Os três grupos são AGREGAÇÃO das classes da regra 8i, sem
  nenhum limiar novo; a tabela "classe → grupo" está na nota da 8i. Para o empate da 8i:
  - ADR, KAST e kills contam em partes iguais;
  - o rating, que só existe sobre rounds inteiros, é o mesmo cálculo da partida (mesma referência,
    mesmo modelo global) sobre os rounds em que o time está inteiro no grupo. O denominador mostra
    quantos rounds são.
