# Decisão 7d: Duas camadas de função, e elas NÃO se misturam

- **ID:** 7d
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** Função estrutural (o trabalho) e traço comportamental (como executa) não se misturam.

## O que vale hoje

O texto diz que `structural_roles` substituiu o `player_roles.py`. Os dois existem hoje: `structural_roles` dá a função por lado e round; `player_roles` dá os rótulos da aba Estilos (`TRAIT_SPECS`, decisão 31) e o "AWPer do time" (decisão 28).

## Texto

7d. **Duas camadas de função, e elas NÃO se misturam.**
   - **Estrutural** (`metrics/structural_roles.py`): qual é o trabalho dele no
     round — AWPer, âncora, coringa, rotativo, entry, trader, lurker, suporte.
     Depende do LADO e sai de posição e tempo.
   - **Comportamental** (`metrics/archetypes.py`): como ele executa esse trabalho
     — carrega piano, baiter, mochila, rei do NT, camper, repick.

   Um âncora pode ser carrega piano ou baiter; um entry pode ser carry ou
   mochila. (O plano de trabalho chama o segundo módulo de
   `behavior_traits.py`; ele é `metrics/archetypes.py` -- nome mantido de
   propósito, para não quebrar imports, testes e esta decisão.) São leituras independentes e **nunca colapsam num ranking único**.

   A função é atribuída por (jogador, round), e a da partida é a DOMINANTE nos
   rounds daquele lado, sempre exibida com a concentração ("âncora em 9 de 12
   rounds de CT"). Round sem função reconhecível fica sem função definida — é
   resultado, não lacuna. Isso **substituiu** o `player_roles.py`, que media a
   mesma coisa por partida e sem separar lado.

   Isto não conflita com a decisão 8: lá o KMeans descobre o grupo e por isso não
   pode batizá-lo; aqui as funções são definidas a priori por critério de jogo
   escrito antes de olhar o dado, e o código só mede quem se encaixa.
