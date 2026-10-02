# Decisão 8c: Sem atacante, o texto nunca usa o nome de alguém

- **ID:** 8c
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Sem atacante o texto não nomeia ninguém; abertura é o primeiro duelo ganho.

## Texto

8c. **Sem atacante, o texto nunca usa o nome de alguém.** E fogo amigo diz
   "morto pelo companheiro X" (5 casos nas 52 partidas), nunca "morreu para X"
   como se X fosse adversário. A ABERTURA do round é o primeiro duelo ganho
   contra o adversário: teamkill, bomba ou queda antes dele não é abertura de
   ninguém (`round_situations` e `opening_kills_with_awp`). O fim de cada
   metade (12, 24, 27, 30...) é marcado na autópsia (`sides.fim_de_metade`). Morte por queda, bomba
   ou dano de zona vem com `attacker_steamid` nulo, e o demo às vezes preenche o
   atacante com a própria vítima. O código diz o que aconteceu ("morreu para a
   bomba") em vez de cair num fallback que nomeia a vítima como matador. Há teste
   varrendo todas as partidas para `attacker_steamid == victim_steamid`.
