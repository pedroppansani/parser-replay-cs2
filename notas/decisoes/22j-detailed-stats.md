# Decisão 22j: Degrau 4 pela página "Detailed stats" da HLTV

- **ID:** 22j
- **Status:** vigente
- **Data:** 2026-09-22
- **Resumo:** Degrau 4: aberturas, multi-kills e headshots exatos; clutch é 1vX com X ≥ 1.

## O que vale hoje

As contagens atuais estão em `data/processed/numeros_citaveis.json` (bloco `escada`).

## Texto

22j. **Degrau 4 pela página "Detailed stats" da HLTV** (`data/reference/
    hltv_detalhado.json`, POR SÉRIE -- os nossos mapas são somados; **8 séries
    inteiras no corpus, 80 jogadores**). Aberturas feitas e sofridas, rounds de
    multi-kill, kills, headshots e mortes: 80/80 exatos (travado em teste).
    As 3 séries acrescentadas em 2026-09-22 (NaVi x Spirit Katowice 03/02, NaVi x
    Aurora StarSeries, Vitality x MongolZ Budapest) vieram POR MAPA
    (`data/reference/brutos/hltv_detalhado_por_mapa_*.tsv`, importadas por
    `scripts/importa_detalhado_mapas.py`, que confere a transcrição pelas
    aberturas, casa o mapa por mapa + elenco + rounds -- nunca pelo K-D -- e
    confere o rating contra o já registrado: 70/70). Elas foram a validação FORA
    DA AMOSTRA das regras de contagem: 30/30 nos quatro campos, sem ajuste.
    Abertura = primeira kill em INIMIGO do round; as da HLTV somam exatamente um
    por round. O que ainda não bate, medido:
    - clutch (1vsX vencido): 32/50 com o antigo "último vivo contra 2+"; 41/50
      contando o 1v1. DECISÃO DO PEDRO: clutch é 1vX com X >= 1, alinhado à
      HLTV, e é a definição ÚNICA do projeto (`metrics/clutch.MIN_ENEMIES_ALIVE`,
      usada também no `build_insights`). DEFINIÇÃO não é PESO: o rei do NT pondera
      cada tentativa pelo X (1v1 perdido pesa 1, 1v3 perdido pesa 3), porque o
      papel é sobre o quase-clutch difícil, não sobre perder duelo; e no round
      mais impressionante o clutch só pontua de 1v2 para cima
      (`MIN_INIMIGOS_CLUTCH_ESPETACULO`). Nos cards, contagem e conversão
      aparecem sempre juntas, com a quebra por X ("1v1: 1/3, 1v2: 0/2"). Com 80
      jogadores: 67/80. As 13 divergências NÃO são espalhadas: 11 são +1 nosso,
      1 é +2 e 1 é -1 -- contamos clutch vencido que a HLTV não conta. Divergência
      concentrada é diagnóstico (há uma regra deles que não temos), não ruído;
      fica em aberto, sem ajuste.
    - assistência: 19/50, faltando 44 no total, 41 delas de FLASH. O evento de
      kill do jogo guarda UM assistente; a HLTV conta a flash à parte. Pela
      cegueira reconstruída, "cegou e a vítima morreu ainda cega para um
      companheiro" acerta o total (+6) mas só 22/50 por jogador.
    - morte trocada (D(t)): 19/50 com a janela de 5s, e 30 a MAIS -- é a origem
      direta do excesso do KAST (8g). O total bate com janela de ~4,25s, mas nenhuma
      janela (2 a 6s), nem "vingada por qualquer um", nem "só a última vítima do
      matador", nem "companheiro matou qualquer inimigo" passa de 20/50 por
      jogador. A HLTV atribui a troca por uma regra que os dados não mostram.
