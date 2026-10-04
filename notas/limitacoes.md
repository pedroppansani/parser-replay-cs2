# Limitações conhecidas e como validar

> Como estavam no CLAUDE.md antes da reestruturação. **O que vale hoje:** o corpus tem 52 partidas (não 9) e a silhueta do agrupamento é 0,195 (`data/global_clusters/model_meta.json`); a contagem de testes está em `data/processed/numeros_citaveis.json`. As demos disponíveis hoje são 13, de partidas profissionais.

## Limitações conhecidas

- São **9 partidas** (1.870 player-rounds). A silhueta do clustering é 0,168
  (k=4) no conjunto — estrutura fraca, e ela **não melhorou com volume**: 1.870
  player-rounds dão praticamente a mesma silhueta que 220. A previsão registrada
  antes (de que melhoraria com mais demos) não se confirmou, e isso muda a
  leitura: estilo de jogo num round é um contínuo, não caixas separadas. Os
  grupos servem como descrição, não como classificação de fronteira nítida.
- 8 das 9 partidas são de 4 mapas (5 Mirage, 2 Ancient, 1 Anubis, 1 Nuke). A
  partição de áreas da Nuke é a menos confiável e nunca foi revisada à mão.
- As demos disponíveis são partidas profissionais do donk, não do Pedro. A
  validação feita foi por consistência (ele lidera ADR e KAST, como esperado) e
  ordem de grandeza, não por memória round a round.
- Caso em aberto: o donk tem o melhor erro angular em briga (14,6°) e o pior
  score de crosshair, porque a mira dele raramente coincide com os ângulos de
  consenso. Para um jogador conhecido por off-angles, pode ser estilo e não
  erro. É julgamento do Pedro.
- Overlay do radar do mapa nos heatmaps depende de `awpy get maps` (download dos
  assets). Sem isso o heatmap funciona em coordenadas de jogo.
- O modelo de probabilidade de vitória supõe **independência entre rounds**, e
  momentum e economia violam isso: depois de perder um round o time perde também
  a compra do seguinte, e a chance real do próximo round não é mais 0,5. Modelar
  economia exigiria um estado (placar, dinheiro, armas) grande demais para 9
  partidas. Fica registrado como simplificação, não como descuido.

## Como validar mudanças

```bash
py -3.12 -m pytest tests/ -v          # 291 testes
py -3.12 -m scripts.process_demo data/raw/match_01.dem --match-id match_01 --from-interim
py -3.12 -m streamlit run legado/app.py
py -3.12 -m scripts.escada_validacao     # rating: contagens contra a HLTV, de baixo para cima
```

Ao mexer numa métrica, confira o efeito na tabela round a round, não só no
agregado — número agregado plausível pode esconder lógica errada.
