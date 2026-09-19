# Material de calibração

Gerado por `py -3.12 -m scripts.material_calibracao`. Cada seção termina com a pergunta que só você responde; as respostas viram constante com data e tamanho de corpus no CLAUDE.md.

## 1. Pisos de função

O rótulo exige **liderar o próprio time** naquela métrica E passar do piso. Por isso a tabela é dos líderes: para cada jogador, em quantas partidas ele liderou o time e em quantas levaria o rótulo com cada corte candidato. Os pisos continuam ABSOLUTOS -- percentil faria uma fração fixa sempre receber rótulo, e "nenhum suporte nesta partida" deixaria de poder acontecer.

### AWPer — hoje `awp_share >= 0.25`
```

AWPer (awp_share) -- piso atual 0.25, candidatos 0.25, 0.35, 0.48, 0.58
  86 lideranças de time em 43 partidas profissionais. Coluna '≥c' = em quantas das partidas que ele liderou o rótulo sai com o corte c.
┌───────────┬────────┬───────┬───────┬───────┬───────┬───────────────────────┬───────────────┐
│ name      ┆ lidera ┆ ≥0.25 ┆ ≥0.35 ┆ ≥0.48 ┆ ≥0.58 ┆ mediana quando lidera ┆ time          │
╞═══════════╪════════╪═══════╪═══════╪═══════╪═══════╪═══════════════════════╪═══════════════╡
│ woxic     ┆ 2      ┆ 2     ┆ 2     ┆ 2     ┆ 0     ┆ 0.54                  ┆ Aurora Gaming │
│ molodoy   ┆ 16     ┆ 12    ┆ 12    ┆ 12    ┆ 7     ┆ 0.57                  ┆ FURIA         │
│ m0NESY    ┆ 12     ┆ 11    ┆ 10    ┆ 7     ┆ 4     ┆ 0.51                  ┆ Falcons       │
│ torzsi    ┆ 10     ┆ 10    ┆ 8     ┆ 5     ┆ 2     ┆ 0.49                  ┆ MOUZ          │
│ w0nderful ┆ 14     ┆ 11    ┆ 10    ┆ 3     ┆ 2     ┆ 0.44                  ┆ Natus Vincere │
│ SH1R0     ┆ 3      ┆ 3     ┆ 3     ┆ 2     ┆ 1     ┆ 0.57                  ┆ Spirit        │
│ sh1ro     ┆ 9      ┆ 8     ┆ 7     ┆ 2     ┆ 1     ┆ 0.45                  ┆ Spirit        │
│ 910       ┆ 2      ┆ 1     ┆ 1     ┆ 0     ┆ 0     ┆ 0.29                  ┆ The MongolZ   │
│ ZywOo     ┆ 16     ┆ 14    ┆ 12    ┆ 7     ┆ 4     ┆ 0.48                  ┆ Vitality      │
└───────────┴────────┴───────┴───────┴───────┴───────┴───────────────────────┴───────────────┘
```
**Sua resposta:** piso de AWPer = ____

### Abre o round — hoje `first_contact_share >= 0.32`
```

Abre o round (first_contact_share) -- piso atual 0.32, candidatos 0.27, 0.31, 0.32, 0.35
  86 lideranças de time em 43 partidas profissionais. Coluna '≥c' = em quantas das partidas que ele liderou o rótulo sai com o corte c.
┌───────────┬────────┬───────┬───────┬───────┬───────┬───────────────────────┬───────────────┐
│ name      ┆ lidera ┆ ≥0.27 ┆ ≥0.31 ┆ ≥0.32 ┆ ≥0.35 ┆ mediana quando lidera ┆ time          │
╞═══════════╪════════╪═══════╪═══════╪═══════╪═══════╪═══════════════════════╪═══════════════╡
│ kyxsan    ┆ 3      ┆ 3     ┆ 2     ┆ 2     ┆ 1     ┆ 0.32                  ┆ Aurora Gaming │
│ KSCERATO  ┆ 4      ┆ 3     ┆ 1     ┆ 1     ┆ 1     ┆ 0.28                  ┆ FURIA         │
│ YEKINDAR  ┆ 9      ┆ 7     ┆ 6     ┆ 4     ┆ 4     ┆ 0.31                  ┆ FURIA         │
│ NiKo      ┆ 3      ┆ 2     ┆ 0     ┆ 0     ┆ 0     ┆ 0.29                  ┆ Falcons       │
│ TeSeS     ┆ 2      ┆ 0     ┆ 0     ┆ 0     ┆ 0     ┆ 0.24                  ┆ Falcons       │
│ kyousuke  ┆ 3      ┆ 2     ┆ 1     ┆ 0     ┆ 0     ┆ 0.27                  ┆ Falcons       │
│ m0NESY    ┆ 3      ┆ 3     ┆ 1     ┆ 0     ┆ 0     ┆ 0.3                   ┆ Falcons       │
│ Brollan   ┆ 2      ┆ 1     ┆ 1     ┆ 1     ┆ 1     ┆ 0.3                   ┆ MOUZ          │
│ Jimpphat  ┆ 2      ┆ 1     ┆ 1     ┆ 1     ┆ 1     ┆ 0.34                  ┆ MOUZ          │
│ Spinx     ┆ 3      ┆ 1     ┆ 0     ┆ 0     ┆ 0     ┆ 0.27                  ┆ MOUZ          │
│ xertioN   ┆ 2      ┆ 2     ┆ 2     ┆ 2     ┆ 1     ┆ 0.35                  ┆ MOUZ          │
│ Aleksib   ┆ 2      ┆ 1     ┆ 0     ┆ 0     ┆ 0     ┆ 0.26                  ┆ Natus Vincere │
│ b1t       ┆ 3      ┆ 1     ┆ 0     ┆ 0     ┆ 0     ┆ 0.27                  ┆ Natus Vincere │
│ iM        ┆ 5      ┆ 4     ┆ 3     ┆ 2     ┆ 1     ┆ 0.31                  ┆ Natus Vincere │
│ w0nderful ┆ 3      ┆ 2     ┆ 1     ┆ 1     ┆ 0     ┆ 0.3                   ┆ Natus Vincere │
│ donk      ┆ 6      ┆ 6     ┆ 4     ┆ 4     ┆ 2     ┆ 0.34                  ┆ Spirit        │
│ zont1x    ┆ 3      ┆ 2     ┆ 2     ┆ 0     ┆ 0     ┆ 0.32                  ┆ Spirit        │
│ ZywOo     ┆ 5      ┆ 3     ┆ 3     ┆ 1     ┆ 1     ┆ 0.32                  ┆ Vitality      │
│ apEX      ┆ 3      ┆ 2     ┆ 2     ┆ 2     ┆ 1     ┆ 0.33                  ┆ Vitality      │
│ flameZ    ┆ 5      ┆ 4     ┆ 4     ┆ 4     ┆ 2     ┆ 0.35                  ┆ Vitality      │
│ ropz      ┆ 3      ┆ 3     ┆ 2     ┆ 2     ┆ 2     ┆ 0.37                  ┆ Vitality      │
└───────────┴────────┴───────┴───────┴───────┴───────┴───────────────────────┴───────────────┘
```
**Sua resposta:** piso de Abre o round = ____

### Suporte de utility — hoje `enemy_blind_seconds >= 20.0`
```

Suporte de utility (enemy_blind_seconds) -- piso atual 20.0, candidatos 20, 40, 54, 81
  86 lideranças de time em 43 partidas profissionais. Coluna '≥c' = em quantas das partidas que ele liderou o rótulo sai com o corte c.
┌───────────┬────────┬─────┬─────┬─────┬─────┬───────────────────────┬───────────────┐
│ name      ┆ lidera ┆ ≥20 ┆ ≥40 ┆ ≥54 ┆ ≥81 ┆ mediana quando lidera ┆ time          │
╞═══════════╪════════╪═════╪═════╪═════╪═════╪═══════════════════════╪═══════════════╡
│ FalleN    ┆ 10     ┆ 10  ┆ 9   ┆ 5   ┆ 3   ┆ 56.66                 ┆ FURIA         │
│ KSCERATO  ┆ 3      ┆ 3   ┆ 2   ┆ 1   ┆ 0   ┆ 45.33                 ┆ FURIA         │
│ YEKINDAR  ┆ 3      ┆ 3   ┆ 2   ┆ 1   ┆ 1   ┆ 43.65                 ┆ FURIA         │
│ NiKo      ┆ 2      ┆ 2   ┆ 1   ┆ 0   ┆ 0   ┆ 40.23                 ┆ Falcons       │
│ kyxsan    ┆ 8      ┆ 8   ┆ 8   ┆ 7   ┆ 6   ┆ 92.54                 ┆ Falcons       │
│ m0NESY    ┆ 2      ┆ 2   ┆ 2   ┆ 2   ┆ 1   ┆ 115.39                ┆ Falcons       │
│ Brollan   ┆ 3      ┆ 3   ┆ 3   ┆ 1   ┆ 0   ┆ 50.91                 ┆ MOUZ          │
│ torzsi    ┆ 4      ┆ 3   ┆ 2   ┆ 2   ┆ 2   ┆ 62.46                 ┆ MOUZ          │
│ xertioN   ┆ 3      ┆ 2   ┆ 1   ┆ 0   ┆ 0   ┆ 30.55                 ┆ MOUZ          │
│ Aleksib   ┆ 7      ┆ 7   ┆ 7   ┆ 3   ┆ 1   ┆ 46.55                 ┆ Natus Vincere │
│ b1t       ┆ 2      ┆ 2   ┆ 1   ┆ 1   ┆ 0   ┆ 54.34                 ┆ Natus Vincere │
│ makazze   ┆ 2      ┆ 2   ┆ 2   ┆ 1   ┆ 0   ┆ 66.88                 ┆ Natus Vincere │
│ w0nderful ┆ 2      ┆ 2   ┆ 1   ┆ 0   ┆ 0   ┆ 36.76                 ┆ Natus Vincere │
│ chopper   ┆ 4      ┆ 4   ┆ 1   ┆ 0   ┆ 0   ┆ 35.76                 ┆ Spirit        │
│ magixx    ┆ 4      ┆ 4   ┆ 4   ┆ 3   ┆ 3   ┆ 91.6                  ┆ Spirit        │
│ bLitz     ┆ 2      ┆ 2   ┆ 1   ┆ 0   ┆ 0   ┆ 39.96                 ┆ The MongolZ   │
│ ZywOo     ┆ 2      ┆ 2   ┆ 1   ┆ 1   ┆ 0   ┆ 50.28                 ┆ Vitality      │
│ apEX      ┆ 11     ┆ 10  ┆ 10  ┆ 8   ┆ 3   ┆ 67.07                 ┆ Vitality      │
│ flameZ    ┆ 3      ┆ 2   ┆ 2   ┆ 2   ┆ 0   ┆ 68.86                 ┆ Vitality      │
└───────────┴────────┴─────┴─────┴─────┴─────┴───────────────────────┴───────────────┘
```
**Sua resposta:** piso de Suporte de utility = ____

### Lurker — hoje `off_team_share >= 0.4`
```

Lurker (off_team_share) -- piso atual 0.4, candidatos 0.4, 0.5, 0.62
  86 lideranças de time em 43 partidas profissionais. Coluna '≥c' = em quantas das partidas que ele liderou o rótulo sai com o corte c.
┌──────────┬────────┬──────┬──────┬───────┬───────────────────────┬───────────────┐
│ name     ┆ lidera ┆ ≥0.4 ┆ ≥0.5 ┆ ≥0.62 ┆ mediana quando lidera ┆ time          │
╞══════════╪════════╪══════╪══════╪═══════╪═══════════════════════╪═══════════════╡
│ KSCERATO ┆ 7      ┆ 5    ┆ 4    ┆ 1     ┆ 0.55                  ┆ FURIA         │
│ YEKINDAR ┆ 6      ┆ 4    ┆ 3    ┆ 1     ┆ 0.45                  ┆ FURIA         │
│ yuurih   ┆ 2      ┆ 2    ┆ 2    ┆ 1     ┆ 0.77                  ┆ FURIA         │
│ NiKo     ┆ 3      ┆ 3    ┆ 3    ┆ 0     ┆ 0.5                   ┆ Falcons       │
│ TeSeS    ┆ 3      ┆ 3    ┆ 3    ┆ 2     ┆ 0.75                  ┆ Falcons       │
│ kyxsan   ┆ 3      ┆ 2    ┆ 1    ┆ 0     ┆ 0.42                  ┆ Falcons       │
│ m0NESY   ┆ 2      ┆ 1    ┆ 1    ┆ 0     ┆ 0.44                  ┆ Falcons       │
│ Brollan  ┆ 3      ┆ 2    ┆ 2    ┆ 1     ┆ 0.56                  ┆ MOUZ          │
│ Jimpphat ┆ 2      ┆ 1    ┆ 0    ┆ 0     ┆ 0.31                  ┆ MOUZ          │
│ Spinx    ┆ 4      ┆ 4    ┆ 4    ┆ 1     ┆ 0.59                  ┆ MOUZ          │
│ Aleksib  ┆ 4      ┆ 2    ┆ 2    ┆ 2     ┆ 0.4                   ┆ Natus Vincere │
│ iM       ┆ 4      ┆ 4    ┆ 4    ┆ 2     ┆ 0.61                  ┆ Natus Vincere │
│ jL       ┆ 3      ┆ 2    ┆ 2    ┆ 1     ┆ 0.57                  ┆ Natus Vincere │
│ makazze  ┆ 2      ┆ 2    ┆ 1    ┆ 1     ┆ 0.62                  ┆ Natus Vincere │
│ chopper  ┆ 3      ┆ 3    ┆ 3    ┆ 3     ┆ 0.75                  ┆ Spirit        │
│ donk     ┆ 2      ┆ 1    ┆ 1    ┆ 0     ┆ 0.35                  ┆ Spirit        │
│ sh1ro    ┆ 2      ┆ 1    ┆ 1    ┆ 1     ┆ 0.41                  ┆ Spirit        │
│ zont1x   ┆ 3      ┆ 3    ┆ 2    ┆ 1     ┆ 0.56                  ┆ Spirit        │
│ apEX     ┆ 5      ┆ 5    ┆ 2    ┆ 1     ┆ 0.45                  ┆ Vitality      │
│ flameZ   ┆ 2      ┆ 2    ┆ 2    ┆ 0     ┆ 0.5                   ┆ Vitality      │
│ mezii    ┆ 3      ┆ 2    ┆ 1    ┆ 0     ┆ 0.4                   ┆ Vitality      │
│ ropz     ┆ 6      ┆ 5    ┆ 5    ┆ 2     ┆ 0.58                  ┆ Vitality      │
└──────────┴────────┴──────┴──────┴───────┴───────────────────────┴───────────────┘
```
**Sua resposta:** piso de Lurker = ____

### Âncora de bomb — hoje `never_left_share >= 0.8`
```

Âncora de bomb (never_left_share) -- piso atual 0.8, candidatos 0.8, 0.86, 0.92, 1
  86 lideranças de time em 43 partidas profissionais. Coluna '≥c' = em quantas das partidas que ele liderou o rótulo sai com o corte c.
┌──────────┬────────┬──────┬───────┬───────┬─────┬───────────────────────┬───────────────┐
│ name     ┆ lidera ┆ ≥0.8 ┆ ≥0.86 ┆ ≥0.92 ┆ ≥1  ┆ mediana quando lidera ┆ time          │
╞══════════╪════════╪══════╪═══════╪═══════╪═════╪═══════════════════════╪═══════════════╡
│ FalleN   ┆ 8      ┆ 8    ┆ 5     ┆ 2     ┆ 2   ┆ 0.88                  ┆ FURIA         │
│ KSCERATO ┆ 2      ┆ 2    ┆ 2     ┆ 2     ┆ 1   ┆ 0.96                  ┆ FURIA         │
│ yuurih   ┆ 5      ┆ 5    ┆ 5     ┆ 3     ┆ 3   ┆ 1.0                   ┆ FURIA         │
│ TeSeS    ┆ 7      ┆ 7    ┆ 6     ┆ 3     ┆ 2   ┆ 0.92                  ┆ Falcons       │
│ kyxsan   ┆ 4      ┆ 3    ┆ 2     ┆ 2     ┆ 1   ┆ 0.88                  ┆ Falcons       │
│ Brollan  ┆ 4      ┆ 4    ┆ 3     ┆ 1     ┆ 1   ┆ 0.89                  ┆ MOUZ          │
│ Jimpphat ┆ 7      ┆ 7    ┆ 5     ┆ 3     ┆ 2   ┆ 0.92                  ┆ MOUZ          │
│ Aleksib  ┆ 4      ┆ 4    ┆ 4     ┆ 2     ┆ 2   ┆ 0.95                  ┆ Natus Vincere │
│ b1t      ┆ 4      ┆ 4    ┆ 3     ┆ 1     ┆ 1   ┆ 0.9                   ┆ Natus Vincere │
│ jL       ┆ 2      ┆ 2    ┆ 2     ┆ 1     ┆ 1   ┆ 0.94                  ┆ Natus Vincere │
│ makazze  ┆ 2      ┆ 2    ┆ 1     ┆ 0     ┆ 0   ┆ 0.88                  ┆ Natus Vincere │
│ chopper  ┆ 2      ┆ 1    ┆ 1     ┆ 0     ┆ 0   ┆ 0.83                  ┆ Spirit        │
│ donk     ┆ 4      ┆ 4    ┆ 2     ┆ 0     ┆ 0   ┆ 0.86                  ┆ Spirit        │
│ magixx   ┆ 5      ┆ 5    ┆ 5     ┆ 5     ┆ 4   ┆ 1.0                   ┆ Spirit        │
│ Mzinho   ┆ 2      ┆ 2    ┆ 2     ┆ 1     ┆ 1   ┆ 0.96                  ┆ The MongolZ   │
│ ZywOo    ┆ 3      ┆ 3    ┆ 3     ┆ 2     ┆ 2   ┆ 1.0                   ┆ Vitality      │
│ apEX     ┆ 5      ┆ 4    ┆ 2     ┆ 2     ┆ 2   ┆ 0.86                  ┆ Vitality      │
│ flameZ   ┆ 3      ┆ 1    ┆ 1     ┆ 0     ┆ 0   ┆ 0.78                  ┆ Vitality      │
│ mezii    ┆ 3      ┆ 3    ┆ 2     ┆ 1     ┆ 1   ┆ 0.92                  ┆ Vitality      │
│ ropz     ┆ 3      ┆ 2    ┆ 2     ┆ 1     ┆ 1   ┆ 0.92                  ┆ Vitality      │
└──────────┴────────┴──────┴───────┴───────┴─────┴───────────────────────┴───────────────┘
```
**Sua resposta:** piso de Âncora de bomb = ____

### Segundo homem — hoje `trade_share >= 0.35`
```

Segundo homem (trade_share) -- piso atual 0.35, candidatos 0.26, 0.33, 0.35, 0.39
  86 lideranças de time em 43 partidas profissionais. Coluna '≥c' = em quantas das partidas que ele liderou o rótulo sai com o corte c.
┌───────────┬────────┬───────┬───────┬───────┬───────┬───────────────────────┬───────────────┐
│ name      ┆ lidera ┆ ≥0.26 ┆ ≥0.33 ┆ ≥0.35 ┆ ≥0.39 ┆ mediana quando lidera ┆ time          │
╞═══════════╪════════╪═══════╪═══════╪═══════╪═══════╪═══════════════════════╪═══════════════╡
│ FalleN    ┆ 2      ┆ 2     ┆ 1     ┆ 1     ┆ 1     ┆ 0.44                  ┆ FURIA         │
│ KSCERATO  ┆ 5      ┆ 3     ┆ 2     ┆ 1     ┆ 0     ┆ 0.32                  ┆ FURIA         │
│ molodoy   ┆ 3      ┆ 2     ┆ 2     ┆ 2     ┆ 2     ┆ 0.62                  ┆ FURIA         │
│ yuurih    ┆ 5      ┆ 4     ┆ 4     ┆ 2     ┆ 1     ┆ 0.33                  ┆ FURIA         │
│ NiKo      ┆ 2      ┆ 2     ┆ 1     ┆ 1     ┆ 0     ┆ 0.33                  ┆ Falcons       │
│ TeSeS     ┆ 4      ┆ 3     ┆ 3     ┆ 2     ┆ 2     ┆ 0.38                  ┆ Falcons       │
│ m0NESY    ┆ 4      ┆ 1     ┆ 0     ┆ 0     ┆ 0     ┆ 0.25                  ┆ Falcons       │
│ Brollan   ┆ 2      ┆ 1     ┆ 0     ┆ 0     ┆ 0     ┆ 0.28                  ┆ MOUZ          │
│ Jimpphat  ┆ 3      ┆ 3     ┆ 3     ┆ 3     ┆ 3     ┆ 0.47                  ┆ MOUZ          │
│ Spinx     ┆ 2      ┆ 2     ┆ 1     ┆ 1     ┆ 1     ┆ 0.38                  ┆ MOUZ          │
│ xertioN   ┆ 2      ┆ 2     ┆ 2     ┆ 2     ┆ 1     ┆ 0.43                  ┆ MOUZ          │
│ Aleksib   ┆ 5      ┆ 3     ┆ 3     ┆ 2     ┆ 1     ┆ 0.33                  ┆ Natus Vincere │
│ b1t       ┆ 3      ┆ 3     ┆ 2     ┆ 2     ┆ 2     ┆ 0.44                  ┆ Natus Vincere │
│ jL        ┆ 2      ┆ 1     ┆ 1     ┆ 1     ┆ 1     ┆ 0.35                  ┆ Natus Vincere │
│ w0nderful ┆ 3      ┆ 3     ┆ 1     ┆ 1     ┆ 1     ┆ 0.31                  ┆ Natus Vincere │
│ donk      ┆ 4      ┆ 4     ┆ 3     ┆ 1     ┆ 0     ┆ 0.33                  ┆ Spirit        │
│ sh1ro     ┆ 4      ┆ 1     ┆ 0     ┆ 0     ┆ 0     ┆ 0.25                  ┆ Spirit        │
│ zont1x    ┆ 2      ┆ 2     ┆ 2     ┆ 1     ┆ 0     ┆ 0.36                  ┆ Spirit        │
│ apEX      ┆ 3      ┆ 2     ┆ 2     ┆ 2     ┆ 1     ┆ 0.36                  ┆ Vitality      │
│ flameZ    ┆ 3      ┆ 1     ┆ 1     ┆ 1     ┆ 0     ┆ 0.25                  ┆ Vitality      │
│ mezii     ┆ 6      ┆ 6     ┆ 3     ┆ 3     ┆ 1     ┆ 0.33                  ┆ Vitality      │
│ ropz      ┆ 4      ┆ 3     ┆ 3     ┆ 3     ┆ 0     ┆ 0.36                  ┆ Vitality      │
└───────────┴────────┴───────┴───────┴───────┴───────┴───────────────────────┴───────────────┘
```
**Sua resposta:** piso de Segundo homem = ____

### Principal fragger — hoje `adr >= 85.0`
```

Principal fragger (adr) -- piso atual 85.0, candidatos 85, 94, 105
  86 lideranças de time em 43 partidas profissionais. Coluna '≥c' = em quantas das partidas que ele liderou o rótulo sai com o corte c.
┌──────────┬────────┬─────┬─────┬──────┬───────────────────────┬───────────────┐
│ name     ┆ lidera ┆ ≥85 ┆ ≥94 ┆ ≥105 ┆ mediana quando lidera ┆ time          │
╞══════════╪════════╪═════╪═════╪══════╪═══════════════════════╪═══════════════╡
│ KSCERATO ┆ 2      ┆ 2   ┆ 2   ┆ 2    ┆ 112.41                ┆ FURIA         │
│ YEKINDAR ┆ 6      ┆ 2   ┆ 2   ┆ 1    ┆ 83.89                 ┆ FURIA         │
│ molodoy  ┆ 3      ┆ 2   ┆ 2   ┆ 1    ┆ 94.06                 ┆ FURIA         │
│ yuurih   ┆ 5      ┆ 3   ┆ 1   ┆ 0    ┆ 86.31                 ┆ FURIA         │
│ kyousuke ┆ 5      ┆ 4   ┆ 3   ┆ 1    ┆ 94.0                  ┆ Falcons       │
│ kyxsan   ┆ 3      ┆ 2   ┆ 2   ┆ 2    ┆ 112.1                 ┆ Falcons       │
│ m0NESY   ┆ 4      ┆ 3   ┆ 0   ┆ 0    ┆ 90.04                 ┆ Falcons       │
│ Jimpphat ┆ 4      ┆ 3   ┆ 1   ┆ 0    ┆ 88.31                 ┆ MOUZ          │
│ Spinx    ┆ 3      ┆ 1   ┆ 1   ┆ 0    ┆ 83.23                 ┆ MOUZ          │
│ xertioN  ┆ 4      ┆ 3   ┆ 0   ┆ 0    ┆ 87.32                 ┆ MOUZ          │
│ Aleksib  ┆ 2      ┆ 0   ┆ 0   ┆ 0    ┆ 71.88                 ┆ Natus Vincere │
│ b1t      ┆ 3      ┆ 3   ┆ 1   ┆ 1    ┆ 85.9                  ┆ Natus Vincere │
│ iM       ┆ 3      ┆ 3   ┆ 2   ┆ 1    ┆ 94.71                 ┆ Natus Vincere │
│ jL       ┆ 3      ┆ 3   ┆ 0   ┆ 0    ┆ 85.85                 ┆ Natus Vincere │
│ makazze  ┆ 2      ┆ 0   ┆ 0   ┆ 0    ┆ 83.55                 ┆ Natus Vincere │
│ donk     ┆ 10     ┆ 10  ┆ 9   ┆ 5    ┆ 104.08                ┆ Spirit        │
│ sh1ro    ┆ 2      ┆ 2   ┆ 2   ┆ 0    ┆ 101.72                ┆ Spirit        │
│ ZywOo    ┆ 14     ┆ 12  ┆ 12  ┆ 6    ┆ 102.72                ┆ Vitality      │
│ flameZ   ┆ 2      ┆ 2   ┆ 1   ┆ 0    ┆ 94.58                 ┆ Vitality      │
└──────────┴────────┴─────┴─────┴──────┴───────────────────────┴───────────────┘
```
**Sua resposta:** piso de Principal fragger = ____

## 2. Nomes dos quatro grupos de estilo

A descrição automática é releitura das médias, não nome de função (decisão 8). As sugestões abaixo são só sugestões: quem nomeia é você, em `clustering/cluster_names.json`.

### Grupo 0 — descrição automática: "longe do time"
- **2749 rounds** (24% do corpus); CT 2011, TR 738
- **O que distingue** (desvios da média geral): avg_distance_from_team 1161.1 contra 709.7 (+1.25); max_distance_from_team 1779.2 contra 1238.9 (+1.09); distinct_places 4.7 contra 6.0 (-0.55); crosshair_score 72.1 contra 68.4 (+0.35)
- **Quem mais concentra** (fração dos próprios rounds, mínimo de 150 rounds no corpus): TeSeS 124 de 310 (40%), Jimpphat 98 de 279 (35%), ropz 111 de 352 (32%), b1t 95 de 303 (31%), yuurih 114 de 369 (31%)
- **Rounds representativos** (mais perto do centro do grupo):
  - match_15 (mirage) round 9, YEKINDAR (ct): 870u do time, 4 regiões, contato 61s, 146 de dano, 2 kills
  - match_01 (ancient) round 11, xhx (ct): 1262u do time, 3 regiões, contato 32s, 0 de dano, 0 kills
  - match_38 (mirage) round 19, Aleksib (ct): 1474u do time, 4 regiões, contato 13s, 0 de dano, 0 kills
  - match_41 (inferno) round 4, m0NESY (ct): 1377u do time, 6 regiões, contato 32s, 100 de dano, 1 kills
  - match_11 (anubis) round 3, tN1R (t): 963u do time, 4 regiões, contato 66s, 0 de dano, 0 kills
- **Sugestões:** Segura sozinho · Âncora isolado · Posição fixa

**Sua resposta:** grupo 0 = ____

### Grupo 1 — descrição automática: "joga por baixo"
- **762 rounds** (7% do corpus); CT 399, TR 363
- **O que distingue** (desvios da média geral): height_score 0.5 contra 0.9 (-2.69); crosshair_score 50.3 contra 68.4 (-1.71); max_distance_from_team 1007.5 contra 1238.9 (-0.47); frac_entering_fight 0.1 contra 0.1 (+0.33)
- **Quem mais concentra** (fração dos próprios rounds, mínimo de 150 rounds no corpus): magixx 30 de 260 (12%), iM 34 de 303 (11%), Spinx 24 de 238 (10%), jL 16 de 165 (10%), b1t 29 de 303 (10%)
- **Rounds representativos** (mais perto do centro do grupo):
  - match_31 (train) round 2, yuurih (t): 636u do time, 5 regiões, contato 32s, 69 de dano, 1 kills
  - match_51 (nuke) round 11, kyousuke (t): 339u do time, 7 regiões, contato 52s, 100 de dano, 1 kills
  - match_21 (nuke) round 18, Wicadia (ct): 735u do time, 8 regiões, contato 12s, 150 de dano, 2 kills
  - match_30 (nuke) round 8, yuurih (ct): 584u do time, 8 regiões, contato 17s, 0 de dano, 0 kills
  - match_16 (nuke) round 9, YEKINDAR (ct): 810u do time, 2 regiões, contato 31s, 126 de dano, 1 kills
- **Sugestões:** Mira fora da altura · Crosshair baixo · —

**Sua resposta:** grupo 1 = ____

### Grupo 2 — descrição automática: "passa por muitas regiões"
- **5276 rounds** (46% do corpus); CT 2306, TR 2970
- **O que distingue** (desvios da média geral): distinct_places 7.4 contra 6.0 (+0.61); time_of_first_contact_s 64.9 contra 47.8 (+0.55); frac_entering_fight 0.1 contra 0.1 (-0.35); avg_distance_from_team 634.0 contra 709.7 (-0.21)
- **Quem mais concentra** (fração dos próprios rounds, mínimo de 150 rounds no corpus): chopper 143 de 225 (64%), w0nderful 191 de 303 (63%), sh1ro 113 de 185 (61%), donk 158 de 260 (61%), zont1x 149 de 260 (57%)
- **Rounds representativos** (mais perto do centro do grupo):
  - match_24 (dust2) round 7, magixx (t): 722u do time, 6 regiões, contato 47s, 4 de dano, 0 kills
  - match_11 (anubis) round 3, iM (ct): 629u do time, 11 regiões, contato 36s, 100 de dano, 1 kills
  - match_10 (dust2) round 9, sh1ro (t): 418u do time, 6 regiões, contato 98s, 172 de dano, 2 kills
  - match_39 (dust2) round 14, iM (t): 395u do time, 8 regiões, contato 90s, 46 de dano, 0 kills
  - match_47 (nuke) round 19, mezii (t): 369u do time, 4 regiões, contato 109s, 0 de dano, 0 kills
- **Sugestões:** Joga o round inteiro · Rodando com o time · Default paciente

**Sua resposta:** grupo 2 = ____

### Grupo 3 — descrição automática: "encosta no adversário cedo"
- **2733 rounds** (24% do corpus); CT 1044, TR 1689
- **O que distingue** (desvios da média geral): max_distance_from_team 789.2 contra 1238.9 (-0.91); time_of_first_contact_s 21.7 contra 47.8 (-0.85); avg_distance_from_team 433.1 contra 709.7 (-0.77); frac_entering_fight 0.2 contra 0.1 (+0.72)
- **Quem mais concentra** (fração dos próprios rounds, mínimo de 150 rounds no corpus): donk666 87 de 187 (47%), YEKINDAR 123 de 369 (33%), xertioN 68 de 238 (29%), kyousuke 80 de 310 (26%), NiKo 80 de 310 (26%)
- **Rounds representativos** (mais perto do centro do grupo):
  - match_01 (ancient) round 15, 9amaterasu9 (t): 344u do time, 8 regiões, contato 12s, 100 de dano, 1 kills
  - match_27 (nuke) round 8, ropz (t): 317u do time, 5 regiões, contato 20s, 53 de dano, 0 kills
  - match_05 (nuke) round 11, gwizdakk (t): 331u do time, 5 regiões, contato 17s, 0 de dano, 0 kills
  - match_49 (mirage) round 6, xertioN (ct): 396u do time, 5 regiões, contato 39s, 124 de dano, 1 kills
  - match_41 (inferno) round 15, m0NESY (t): 200u do time, 5 regiões, contato 46s, 174 de dano, 1 kills
- **Sugestões:** Pressão cedo · Entrada em bloco · Executa junto

**Sua resposta:** grupo 3 = ____

## 3. Rótulos de força do arremesso

2268 arremessos em 6 partidas. Os grupos saem por moda (decisão 5); os rótulos foram aplicados PELA ORDEM (mais lento = curto) e estão marcados "(a confirmar)" no código até você responder.

| Grupo | Centro | Arremessos | Exemplo |
|---|---|---|---|
| longo (a confirmar) | 675 u/s | 2066 | iM, flash, match_38 round 20 (0:26), agachado, parado |
| médio (a confirmar) | 443 u/s | 100 | YEKINDAR, he, match_43 round 20 (1:15), em pé, parado |
| curto (a confirmar) | 198 u/s | 102 | SH1R0, he, match_38 round 7 (0:24), agachado, parado |

```
   0-50   u/s |                                                       1  curto (a confirmar)
  50-100  u/s |                                                       1  curto (a confirmar)
 100-150  u/s |                                                       4  curto (a confirmar)
 150-200  u/s | #                                                    43  curto (a confirmar)
 200-250  u/s | #                                                    51  curto (a confirmar)
 250-300  u/s |                                                       1  curto (a confirmar)
 300-350  u/s |                                                       1  médio (a confirmar)
 350-400  u/s |                                                       0  médio (a confirmar)
 400-450  u/s | ##                                                   83  médio (a confirmar)
 450-500  u/s |                                                      14  médio (a confirmar)
 500-550  u/s |                                                       3  médio (a confirmar)
 550-600  u/s |                                                       4  longo (a confirmar)
 600-650  u/s | #                                                    49  longo (a confirmar)
 650-700  u/s | ################################################## 1920  longo (a confirmar)
 700-750  u/s | ##                                                   84  longo (a confirmar)
 750-800  u/s |                                                       8  longo (a confirmar)
 800-850  u/s |                                                       1  longo (a confirmar)
```

**Sua resposta:** curto/médio/longo pela ordem está certo? ____

## 4. Teste do comando de console

Arremesso: **jL**, smoke, **match_38** (de_mirage) round 2, 0:33 do round (tick 9288). Ancoragem com resíduo de 0.02u, em pé, parado.

1. Servidor local no mapa, com:

```
sv_cheats 1; mp_warmup_end; mp_freezetime 0; sv_infinite_ammo 1; sv_grenade_trajectory_prac_pipreview 1
```

2. Com a smoke na mão, sem se mover:

```
setpos -722.82 -2186.60 -179.97; setang -2.27 86.24 0
```

3. Solte com o **botão esquerdo** (arremesso cheio), em pé, parado.

**Certo:** a smoke para em (-655, -1159, -166). O preview da trajetória mostra o ponto antes de você soltar.

**Se errar, me mande:** a saída do `getpos` logo depois do `setpos`; onde a smoke caiu (nome do lugar); e se o erro foi de DISTÂNCIA (curta ou longa demais -> altura ou pitch) ou de LADO (esquerda ou direita -> yaw).

**Sua resposta:** funcionou? ____
