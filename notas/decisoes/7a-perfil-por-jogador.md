# Decisão 7a: O perfil por jogador é a leitura principal dos dados comportamentais; o agrupamento existe para DESCOBRIR os grupos, não para descrever pessoas

- **ID:** 7a
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** O perfil por jogador é a leitura; taxa sempre com bruto, referência e marca de amostra fraca.

## Texto

7a. **O perfil por jogador é a leitura principal dos dados comportamentais; o
   agrupamento existe para DESCOBRIR os grupos, não para descrever pessoas.**
   As médias de um grupo ("distância média do time 1.100u", "8 regiões") não
   pertencem a jogador nenhum: os rounds de um mesmo jogador se espalham por
   todos os grupos. Quem responde sobre uma pessoa é `metrics/player_profile.py`,
   com a frequência de cada comportamento nos rounds DELE ("puxa AWP em 40% dos
   rounds"). Ao adicionar uma leitura sobre jogador, ela vai no perfil — não em
   mais uma média de cluster.

   Três contratos do perfil, e nenhum é decoração:
   - **taxa sempre com o bruto** (`_n` e `_d`): com 22 rounds, 41% e 50% são o
     mesmo número, e só o percentual inventa precisão;
   - **taxa sempre com referência** (`_ref`, mediana dos OUTROS jogadores,
     leave-one-out): "60% longe do time" não diz se é muito ou pouco;
   - **amostra pequena marcada** (`_fraco`): 1 de 1 não é 100%.

   E lado importa: distância, ancoragem e contato cedo saem também em `_ct` e
   `_t`, com a referência calculada dentro do lado.

   Os grupos chegam à pessoa por `player_profile.cards_de_estilo`: um card por
   grupo com os 3 jogadores de MAIOR FRAÇÃO dos próprios rounds nele ("7 de 22
   rounds — 32%"; ordenar pela contagem favoreceria quem jogou mais rounds), e
   a lista de quem não passa de `CONCENTRACAO_MINIMA_GRUPO` em grupo nenhum
   ("sem grupo dominante"). Texto todo gerado em Python.
