# Round swing por jogador: investigação e proposta (RS0)

Só leitura. Scripts: `scripts/calibracao/rs0_swing_por_round.py`, `rs0_analise.py`, `rs0_modelos.py`, `rs0_round_real.py`. Logs em `notas/logs/rs0-*.log`. Um round real passo a passo: `2026-11-12-round-swing-round-real.md`. Prints: `2026-11-12-round-swing-prints-para-o-pedro.md`.

## A descoberta que muda a fase
**O Round Swing já existe no projeto e já foi conferido com o oficial da HLTV.** É o sexto sub-rating do rating (`metrics/rating.py`: `swing_por_evento`, `ModeloDeRound`; decisões 22, 22a, 22b, 22f, 22h, 22k, 22l). Ele divide o crédito de cada kill (55% matador, 25% dano, 10% flash, 10% troca; a vítima paga tudo; o fim do round vai para quem terminou vivo) e usa um modelo de chance de vencer o round (regressão logística com 8 entradas). O que NÃO existe é mostrar o número em pontos percentuais por round: hoje ele só entra no rating como razão centrada em 1,00 (`round_swing` em `rating_sub`, sem tela). Então a fase seguinte é expor e estabilizar o que há, não construir.

## 1. O que já existe
- **Modelo do gráfico antigo:** `metrics/win_probability.py` ainda está no código (348 linhas). Ele é a chance de vencer a PARTIDA (programação dinâmica sobre o placar, p do round = 0,5 neutra). **Não serve para o swing**, que precisa da chance de vencer o ROUND com vivos, bomba e economia. A curva saiu do site em 16/10/2026 (commit `81beca2a`), virou as barras "Quanto cada round pesou" e continua no histórico do git. O modelo que serve é o `ModeloDeRound` (rating), gravado em `metrics/rating_reference.json`.
- **Rating:** segue o **3.0** da HLTV como reimplementação própria (decisão 22; texto obrigatório "implementação própria da metodologia do Rating 3.0 (HLTV)" no resumo do módulo e em `rating_info` do insights). Pesos ajustados contra 43 partidas (erro 0,079 fora da amostra, correlação 0,966).

## 2. O que a HLTV publicou (e o que não)
Fonte lida: "Introducing Rating 3.0", https://www.hltv.org/news/42485/introducing-rating-30 (20/08/2025). Citações:
- Round Swing: "a metric that looks at a team's win probability before and after each kill with knowledge of the map, side, and economy of each round."
- Crédito: "divided based on the final point of damage, the damage share, flash assists, and whether it was a trade kill."
- Modelo: entram "each team's economic situation, whether the bomb is planted, how many players are alive on each team, and which map the player is on".
- "Round Swing is zero-sum"; um exemplo de salvamento (a chance sobe de 48% para 89% quando o time perde mas os jogadores sobrevivem); escala em "%" (donk +3,79%, ZywOo +3,69%; jogadores comuns entre −1,5% e +1,5% em amostras grandes); abertura ≈ +20%, clutch 1v1 até +50%.
- **Não publicado:** os pesos do crédito, a fórmula e os parâmetros do modelo, o tempo como entrada, crédito de plant/defuse, mortes além do "zero-sum" e do exemplo do salvamento.
- **Ajuste de outubro de 2025: não achei.** A leitura só alcançou o artigo de agosto e a página de 2010; não tenho busca na web neste ambiente. Peço o link ao Pedro. Os prints já transcritos são de setembro de 2026, então refletem a versão em vigor.
Onde a fórmula não é pública, a nossa é a do projeto (decisões 22a e 22f).

## 3. O modelo de chance de vitória
- **Dado:** 52 partidas, 1.151 rounds com kill, **7.768 estados** (um por kill, de cada lado: 15.536 linhas). Por mapa: Mirage 361 rounds, Dust2 222, Nuke 195, Inferno 124, Anubis 103, Ancient 66, Overpass 46, Train 34. Por mapa isolado é pouco (menos de 400 rounds); os mapas juntos bastam para o modelo atual.
- **Usado em cada instante:** diferença e razão de vivos, equipamento (valor do time), bomba com sinal, lado, eliminação, tempo do round e da bomba. Mapa: não usado.
- **Opção A, tabela suavizada** (vivos × vivos × bomba × lado, encolhida para a taxa do lado, K = 20): Brier **0,1369**, AUC 0,888.
- **Opção B, regressão logística** (a de hoje): Brier **0,1245**, AUC 0,907. Com lado×mapa: 0,1250 (não melhora). **Recomendo a B, a que já está adotada.**
- **Como saber se presta:** 10 dobras agrupadas por partida (nenhuma partida dos dois lados da divisão). Calibração (previsto → observado): 0,0–0,1: 3,3% → 3,5%; 0,1–0,2: 14,7% → 15,0%; 0,3–0,4: 34,7% → 35,7%; 0,5–0,6: 54,9% → 55,3%; 0,8–0,9: 85,2% → 87,2%; 0,9–1,0: 96,7% → 97,7%. **Falha conhecida:** em 0,2–0,3 prevê 24,9% e o observado é 30,9% (o time em desvantagem vence mais do que o modelo diz); em 0,7–0,8 prevê 75,2% e dá 71,4%. Deixar UMA partida fora (52 dobras) em vez de 10 é um rerun barato, que faço na RS1.

## 4. A divisão do crédito
Já definida e testada (decisão 22f; pesos 55/25/10/10, constantes em `metrics/rating.py`). Morte: a vítima paga a variação inteira. Fim do round: o salto até 100% vai, em partes iguais, a quem terminou vivo. Plant e defuse: não são eventos (o salto do plant não é de ninguém; 22f testou e não muda o erro). Round real completo, com a chance antes e depois: arquivo `round-real`.

## 5. A conferência com a HLTV: já feita em 33 partidas
Medida agora (script `rs0_analise.py`, 330 jogador-partidas em 33 partidas, números em p.p. por round):
- correlação **0,903** (Spearman 0,876); erro médio absoluto **1,71 p.p.**; viés 0,00; inclinação 1,02; desvio do oficial 4,45 contra 5,04 do nosso.
- Dentro de cada partida a correlação tem mediana 0,90 (pior 0,36, melhor 0,99). Maiores erros: match_47 apEX (oficial +1,33, nosso +6,93), ropz (+7,62 contra +1,98), match_52 apEX (−11,43 contra −5,85).
- **O que conta como "bate bem o bastante":** correlação ≥ 0,85 e erro médio ≤ 2 p.p. já passam hoje. O número nunca será igual (modelo e pesos deles são fechados, e eles usam o mapa).
- **Prints:** faltam 10 partidas profissionais (match_10, 11, 12, 14–20) para fechar as 43; lista no arquivo `prints-para-o-pedro`.

## 6. A incerteza (a parte que mais pesa)
Medida em 116 jogadores (mediana 24 rounds; 31 com 100+ rounds):
- Desvio do swing de UM round: **19,9 p.p.**. Erro padrão da média: 10 rounds ±6,3; **20 rounds (uma partida) ±4,4**; 60 ±2,6; **100 ±2,0**; 200 ±1,4.
- Confiabilidade (duas metades disjuntas): 20 rounds r = 0,11; 50 r = 0,38; 80 r = 0,50; **120 r = 0,62**.
- Entre jogadores com 100+ rounds a média vai de −4,3 a +7,5 (desvio 2,5); tirando o ruído de amostragem, a diferença real entre jogadores é de uns 1,7 p.p., compatível com o "entre −1,5% e +1,5%" da HLTV.
**Consequência:** o swing de UMA partida descreve o que aconteceu (e bate com a HLTV a 0,90) mas não mede habilidade; um número de Perfil só é razoavelmente estável com ~100+ rounds. Proposta: na tabela da partida, mostrar o número com o aviso "uma partida: varia ±4 p.p. por sorte" no texto da seção, não em cada linha; no Perfil, mostrar com "±" a partir de 30 rounds (o mínimo atual do rating, `MIN_ROUNDS_CONFIAVEL`) e destacar como estável só com 100+; abaixo de 30, não mostrar o número ("poucos rounds").

## 7. Onde aparece
Tabela da partida e Perfil, ao lado do rating, como "+4,2 p.p. por round" (com sinal; a média da partida soma ≈ 0). Frase de rascunho: "Round swing: quanto o jogador mexeu, por round, na chance de o time vencer o round; implementação própria, o número pode diferir do da HLTV." Selo "implementação própria" igual ao do rating. Não volta nenhum gráfico de chance.
Observação de linguagem: usar "pontos percentuais" (p.p.), como as decisões do projeto; a HLTV escreve "%".

## 8. Fases propostas
- **RS1:** expor `sub_round_swing` em p.p. por round no `insights.json` de cada jogador (campo novo) e agregar por jogador no corpus, com o número de rounds, o erro padrão e a regra de "poucos rounds"; teste de integridade (soma zero por partida) e o teste que já compara com o oficial. Impressão: só linhas novas. Suíte inteira no resultado do merge.
- **RS2:** o número no site (tabela da partida e Perfil), texto, portão de capturas nos 3 tamanhos e no celular.
- **RS3:** a conferência estendida às 43 partidas com os prints novos, e o rerun "deixa uma partida fora" do modelo.
- **Opcional, depois de RS3:** testar plant/defuse como evento e a calibração em 0,2–0,3 (um termo de desvantagem), só se a medida contra a HLTV melhorar.

## O que o dado não sustenta
- Habilidade individual por partida (±4,4 p.p. de ruído contra ~1,7 p.p. de diferença real entre jogadores).
- Um modelo por mapa (34 a 361 rounds) e o efeito do mapa (testado: não melhora, 0,1250 contra 0,1245).
- Comparar com a versão de outubro de 2025 da HLTV: não achei o texto e os prints são de uma data só.

## Decisões abertas para o Pedro
1. **Escopo da fase:** (a) só expor o que existe (recomendo); (b) rever também o modelo (tabela A ou termo para 0,2–0,3). Recomendo (a): o erro contra a HLTV já está em 1,71 p.p.
2. **Quando mostrar no Perfil:** (a) a partir de 30 rounds com "±" e "estável" só com 100+ (recomendo); (b) só com 100+ (31 de 116 jogadores); (c) sempre.
3. **Na tabela da partida:** (a) mostrar o número da partida com o aviso de ±4 na seção (recomendo, é o que a HLTV faz); (b) não mostrar por partida, só no Perfil.
4. **Prints:** completar as 43 partidas (10 prints) agora ou na RS3? E o link da atualização de outubro de 2025, se tiver.
5. **Nome:** "round swing" com o texto em p.p. por round, ou outro nome para não confundir com o da HLTV.
