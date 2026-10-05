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
- **Na partida**, a comparação é a da aba Perfil: dois jogadores DAQUELA partida, com a régua do
  corpus. É estado da tela, não o seletor de base que a decisão 30 proíbe.
- **Entre partidas**, só em `jogadores.html` (o "lugar separado" da decisão 30): por steamid, razão
  das somas, intervalo por bootstrap das partidas (semente fixa) e encolhimento para a média da
  função com peso m / (m + k), k por métrica estimado no corpus (variância dentro / entre jogadores).
  Sem variação entre jogadores (k indefinido), a página diz que o corpus não separa ninguém.
- Rótulos das taxas do perfil em `metrics/player_profile.ROTULOS_DAS_TAXAS`, para as duas páginas.
- **Parado:** desempenho por eco/força/compra cheia. A regra 8i não tem essas classes (são grupo da
  arma mais cara × colete), e o corte é decisão do Pedro.
