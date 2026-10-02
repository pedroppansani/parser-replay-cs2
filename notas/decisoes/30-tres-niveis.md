# Decisão 30: A página da partida tem TRÊS NÍVEIS, e eles não se misturam

- **ID:** 30
- **Status:** vigente
- **Data:** 2026-09-24
- **Resumo:** Página da partida: números só dela; régua anônima do corpus; sem seletor.

## Texto

30. **A página da partida tem TRÊS NÍVEIS, e eles não se misturam** (decisão do
    Pedro, 2026-09-24):
    1. **os números do JOGADOR são só da partida aberta.** É PROIBIDO puxar o
       histórico dele em outras partidas para dentro da análise da partida --
       "40% em 22 rounds" e "40% em 180 rounds" não são a mesma afirmação, e
       misturar as duas numa tela só é o jeito mais fácil de afirmar sobre a
       partida o que veio de outras. O `player_profile_summary` (perfil
       acumulado) SAIU do payload;
    2. **a régua é a distribuição agregada e ANÔNIMA do corpus**
       (`metrics/perfil_reference.json`, ajustada por
       `scripts/fit_perfil_reference.py`: só medianas, nenhum nome, nenhum
       steamid). Antes a referência era a mediana dos OUTROS NOVE jogadores da
       mesma partida, o que responde "ele está acima dos adversários DE HOJE" --
       o mesmo 40% virava destaque ou banalidade conforme quem entrou em quadra;
    3. **sem seletor.** A régua do corpus é usada quando há corpus; quando a
       partida é a única, cai na mediana dos outros jogadores dela e a página
       AVISA em vez de afirmar ("comparado só com os outros jogadores desta
       partida -- amostra fraca"). O seletor de base ("só esta partida" x "todas
       as partidas processadas") foi REMOVIDO: escolher a base é escolher a
       conclusão, e a escolha certa não depende de quem está olhando.
    Visão agregada por jogador (todas as partidas) continua existindo, mas só em
    lugar separado e explícito -- nunca dentro da página de uma partida.
    A origem da régua viaja no perfil (`regua_origem`, `regua_partidas`,
    `regua_jogador_partidas`) e o texto do aviso é montado no JS a partir desses
    números, sem frase escrita no template (decisão 18).
