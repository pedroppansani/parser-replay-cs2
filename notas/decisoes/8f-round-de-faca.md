# Decisão 8f: Round de faca gravado na demo sai no parse, e os rounds são renumerados

- **ID:** 8f
- **Status:** vigente
- **Data:** 2026-09-18 (entrada no arquivo; o texto não traz data)
- **Resumo:** Round de faca sai no parse e os rounds são renumerados.

## Texto

8f. **Round de faca gravado na demo sai no parse, e os rounds são renumerados.**
   Algumas demos profissionais trazem a faca que decide o lado como round 1. A
   regra de lados (`metrics/sides.py`) supõe que o round 1 é o primeiro do
   jogo, e depois da faca o vencedor escolhe o lado: Vitality x Spirit (Mirage)
   saía 15-9 em 24 rounds, placar impossível; sem a faca, 13-10 e K-D idêntico
   ao da HLTV. Critério: primeiro round com dano e nenhum dano de arma de fogo
   (`parsing.remove_round_de_faca`, aplicado em `save_interim`). Há teste que
   varre todas as partidas atrás de placar impossível -- ele pega esta classe
   de bug (lado errado, round a mais) em qualquer demo nova.
