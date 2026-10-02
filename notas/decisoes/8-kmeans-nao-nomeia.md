# Decisão 8: O KMeans não nomeia os grupos

- **ID:** 8
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** O KMeans não nomeia grupos; o nome é do Pedro (`cluster_names.json`).

## Texto

8. **O KMeans não nomeia os grupos.** Apelido de jogo ("lurker", "âncora",
   "entry") é interpretação e cabe ao Pedro, via `clustering/cluster_names.json`.
   **Não gere rótulos automáticos.**

   O nome que aparece é uma DESCRIÇÃO derivada da medição (`describe_clusters`):
   "longe do time, chega a se afastar muito" é releitura dos números, não
   leitura de jogo. Ela sai do perfil GLOBAL, não do recorte da partida, senão o
   mesmo grupo mudaria de texto de uma página para a outra.

   O `cluster_names.json` entra no payload do site: sem isso o arquivo só teria
   efeito no dashboard local e a nomeação nunca chegaria à página.

   **O agrupamento não tem mais seção própria no site.** Ele existe como insumo:
   o único lugar onde aparece é o "jeito de jogar mais frequente" da aba Perfil.
   A seção que o desenhava foi removida porque descrevia GRUPOS DE ROUNDS — média
   que não pertence a jogador nenhum — e o perfil por jogador responde a mesma
   pergunta direto. Junto saiu a última ocorrência da palavra "cluster" no texto
   visível das páginas, e as 220 atribuições round a round que iam no payload de
   cada página sem ninguém ler.
