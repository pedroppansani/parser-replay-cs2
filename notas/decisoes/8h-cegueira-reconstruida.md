# Decisão 8h: Cegueira por flash é RECONSTRUÍDA nas demos de campeonato

- **ID:** 8h
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Cegueira é reconstruída de `flash_duration` nas demos sem `player_blind`.

## Texto

8h. **Cegueira por flash é RECONSTRUÍDA nas demos de campeonato** (elas não
   gravam `player_blind`; só as de FACEIT gravam). `parsing/cegueira.py`:
   `flash_duration` recebe a duração TOTAL no tick em que a flash pega, fica
   parado e volta a zero no fim -- e TROCA de valor sem passar por zero quando
   outra flash pega o jogador ainda cego. Início = toda mudança para um valor
   positivo (não só 0 -> positivo). Dono = detonação de flash no mesmo tick
   (janela de 2 ticks); duas candidatas indistinguíveis deixam a cegueira SEM
   DONO. Validado contra o evento real nas 9 de FACEIT: **1.578 de 1.578 com o
   arremessador certo e a duração exata, nenhuma inventada**. Nas 43
   profissionais: 11.736 cegueiras, 41 (0,35%) sem dono por detonação
   simultânea. A tabela reconstruída leva `origem = "reconstruida"`. Medido: a
   proporção de companheiros cegados por flash lançada é a mesma do evento real
   (0,32 contra 0,34) -- cegar o próprio time é assim frequente mesmo.
