# Decisão 26: Invariantes sobre o corpus inteiro

- **ID:** 26
- **Status:** vigente
- **Data:** 2026-09-20 (entrada no arquivo; o texto não traz data)
- **Resumo:** Dez invariantes sobre o corpus inteiro (`test_invariantes_corpus.py`).

## Texto

26. **Invariantes sobre o corpus inteiro** (`tests/test_invariantes_corpus.py`):
    o que não pode acontecer em partida nenhuma, por mais demos que entrem.
    São dez, e cada um corresponde a um bug que já aconteceu ou que aconteceria
    em silêncio -- tempo negativo no timeline, atacante igual à vítima, warmup
    dentro das métricas, KAST fora de 0-100, nulo em métrica final, média do
    rating longe da OFICIAL, a curva de probabilidade indo de 0,5 ao resultado,
    e os três de identidade. **Já pagou na primeira execução**: foi o invariante
    da curva que achou a prorrogação terminando em 100% para o time errado
    (decisão 19e), que passou meses invisível porque nenhuma das 9 partidas
    iniciais tinha ido para OT.
    O da média do rating compara com a média OFICIAL dos mesmos jogador-partidas
    (1,0720 nosso contra 1,0726 da HLTV em 430), não com 1,00: o corpus é de
    times de topo e não é amostra neutra -- exigir 1,00 seria pedir que a nossa
    escala discordasse da oficial. Sem `data/processed/` os testes são
    pulados, nunca quebram.
