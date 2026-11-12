# Round swing: um round real passo a passo (RS0)

Partida `match_43` (FURIA × Vitality, Mirage), **round 8**, gerado por `py -3.12 -m scripts.calibracao.rs0_round_real match_43 8` com a regra que o projeto JÁ usa (`swing_por_evento`, decisão 22a/22f/22k) e o modelo gravado em `metrics/rating_reference.json`.
O round tem as quatro formas de crédito (kill, dano, flash, troca), a bomba plantada e o fim do round. Time A = FURIA, time B = Vitality. "Chance" é a do time que MATOU, no instante da kill, antes e depois dela.

Regra: a variação da chance do evento é UMA só; a vítima paga tudo; o crédito vai 25% para quem deu dano antes (dividido pelo dano de cada um, mínimo 20), 10% para quem cegou a vítima nos 3 s antes, 10% para o matador se a kill trocou a morte de um companheiro, e o matador fica com o resto (no mínimo 55%). Ao fim do round o salto da chance até 100% vai, em partes iguais, para quem terminou vivo (o time que ganhou recebe, o que perdeu paga).

| hora | evento | vivos A×B | chance de quem matou | variação | quem recebe (p.p.) |
|---|---|---|---|---|---|
| 1:29 | ZywOo mata molodoy (AWP) | 5×5 → 4×5 | B: 39,8% → 63,3% | +23,5 | ZywOo +23,51 (kill); molodoy −23,51 |
| 0:21 | flameZ mata KSCERATO | 4×5 → 3×5 | B: 65,7% → 84,8% | +19,1 | flameZ +17,20; apEX +1,91 (flash); KSCERATO −19,11 |
| 0:20 | FalleN mata flameZ (AWP) | 3×5 → 3×4 | A: 15,2% → 31,5% | +16,3 | FalleN +8,98 (kill) +1,63 (troca); yuurih +4,08 (dano) +1,63 (flash); flameZ −16,33 |
| 0:19 | yuurih mata apEX | 3×4 → 3×3 | A: 31,5% → 57,6% | +26,1 | yuurih +26,13; apEX −26,13 |
| 0:04 | ropz mata YEKINDAR (bomba plantada) | 3×3 → 2×3 | B: 23,1% → 52,7% | +29,6 | ropz +29,58; YEKINDAR −29,58 |
| 0:02 | ZywOo mata FalleN | 2×3 → 1×3 | B: 48,2% → 83,6% | +35,5 | ZywOo +26,59; flameZ +8,86 (dano); FalleN −35,45 |
| 0:01 | yuurih mata mezii | 1×3 → 1×2 | A: 17,5% → 40,8% | +23,3 | yuurih +23,31; mezii −23,31 |
| 0:00 | ropz mata yuurih | 1×2 → 0×2 | B: 52,4% → 94,2% | +41,8 | ropz +27,20 (kill) +4,18 (troca); apEX +10,46 (dano); yuurih −41,85 |
| fim | a Vitality vence | | | | ropz +2,88; ZywOo +2,88 (vivos); yuurih −5,77 (o único vivo do time que perdeu) |

**Total do round (p.p.):** ropz +63,85 · ZywOo +52,99 · flameZ +9,73 · yuurih +7,55 · apEX −13,76 · KSCERATO −19,11 · mezii −23,31 · molodoy −23,51 · FalleN −24,84 · YEKINDAR −29,58. **Soma: 0,0000.**

## O que o round mostra
- **Cada linha soma zero** entre os dez: o que um time ganha o outro perde. É o "zero-sum" que a HLTV diz no artigo.
- **O plant não vira evento.** Entre 0:19 e 0:04 a bomba foi plantada (às 0:14) e o 3×3 passou de 57,6% para o A (FURIA, TR) a cerca de 77% (23,1% para o B): esses ~19 p.p. não são de ninguém, porque a chance antes e depois de cada kill é medida no MESMO instante. A decisão 22f testou o plant como evento e "não muda nada" no erro contra a HLTV; a HLTV também não publica crédito para plant/defuse.
- **Quem morre ainda recebe dano creditado:** apEX levou +10,46 por dano na kill das 0:00 mesmo morto, como a regra pede ("quem deu dano").
- **O número por round é grande** (dezenas de p.p. num round decidido por clutch). O que a HLTV mostra é a média por round do jogador (ordinariamente entre −1,5 e +1,5 em amostras grandes): aqui, ropz + ZywOo somam +117 num round só, e a média por round dilui isso em ~22 rounds.
