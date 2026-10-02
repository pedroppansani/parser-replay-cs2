# Decisão 7h: O trader é definido POR RELAÇÃO ao entry, e a proximidade sozinha não basta

- **ID:** 7h
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** Trader é o segundo homem do entry; proximidade sozinha fica abaixo do piso.

## Texto

7h. **O trader é definido POR RELAÇÃO ao entry, e a proximidade sozinha não
   basta.** Ele é o segundo homem da entrada: entra junto com o entry para que a
   morte do entry não saia de graça. A identificação é a distância até o entry no
   instante em que o entry toma o primeiro contato (`RAIO_ATRAS_DO_ENTRY`, o
   mesmo raio de apoio do resto do projeto); a troca efetiva é o RESULTADO, não a
   identificação — trader que tentou e não conseguiu continua sendo o trader
   daquele round, do mesmo jeito que um entry que perde a abertura continua
   sendo entry.

   Os pesos são escolhidos para que proximidade sozinha (0,40) fique ABAIXO do
   piso (0,45): andar perto do entry acontece em qualquer execução de bomb, e sem
   ser o segundo no contato nem trocar a morte, isso é o time junto e não um
   trader. Junto disso, o peso de trade SAIU do suporte: com ele nos dois, as
   duas funções disputavam o mesmo sinal e o resumo por lado passava a depender
   de arredondamento. Medido: o trader aparece em 97 dos 935 rounds de TR e é a
   função dominante em 14 dos 90 jogador-lados; a cobertura de TR subiu de 41%
   para 47%.
