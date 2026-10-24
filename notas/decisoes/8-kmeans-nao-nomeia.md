# Decisão 8: O KMeans não nomeia os grupos

- **ID:** 8
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** O KMeans não nomeia grupos; o nome é do Pedro (`cluster_names.json`).

## O que vale hoje

### Reajuste nas 52 partidas (2026-10-19, item 2 da calibração, autorizado pelo Pedro)

`py -3.12 -m scripts.fit_global_clusters` nas 52 partidas (11.520 jogador-rounds) reproduz o modelo
gravado: índice de Rand ajustado 1,000 contra a atribuição anterior, 11.520 de 11.520 jogador-rounds
no mesmo grupo e com o mesmo número, silhueta 0,196 nos dois. Nenhuma atribuição muda:

| perfil | grupo | jogador-rounds antes | depois |
|---|---|---|---|
| longe | 0 | 3.049 | 3.049 |
| mira | 1 | 1.112 | 1.112 |
| junto | 2 | 4.033 | 4.033 |
| roda | 3 | 3.326 | 3.326 |

O modelo gravado já era o das 52 (desde o reajuste de 2026-10-03, decisão 7b); o "ajustado nas 9
partidas de FACEIT" do material é texto fixo de `pesquisa/proposta_grupos.py`. A seção 2 do material
foi gerada em 2026-09-26, antes daquele reajuste, e por isso numera os grupos de outro jeito (lá
"mira" é o grupo 0; hoje é o 1).

O reajuste só mexeu no último bit dos centróides (até 2,2e-16), e isso varia entre duas execuções no
mesmo processo: o KMeans soma em várias threads. Com uma thread só (`threadpool_limits(1)`), cinco
execuções dão o mesmo modelo. O `global_model.json` gravado ficou como estava (o reajuste não o muda
além desse ruído); tornar o ajuste determinístico é correção pendente da decisão 28.

### Os nomes, presos ao PERFIL (resposta do Pedro à seção 2 do material, 2026-10-19)

O nome segue o perfil, não o número do grupo: num reajuste que renumere, cada nome vai para o grupo
que tem a mesma assinatura. Conferido no modelo reajustado pelas features que distinguem cada grupo
(|z| contra a média do corpus; o reconhecimento é `pesquisa/proposta_grupos.PERFIS`, e cada grupo
casou com um perfil só):

| perfil | nome | grupo | o que o distingue (z) |
|---|---|---|---|
| mira | Mira fora da altura | 1 | mira na altura da cabeça −2,29; placement −1,54 |
| junto | Junto e rápido | 2 | maior distância do time −0,75; distância média −0,65; 1º contato −0,65; entrando em briga +0,54 |
| longe | Segura longe do time | 0 | distância média do time +1,25; maior distância +1,16 |
| roda | Roda o mapa | 3 | regiões visitadas +0,89; 1º contato +0,73 |

Só o nome do perfil "junto" mudou ("Entra em bloco" → "Junto e rápido"); os outros três já estavam
no grupo certo.

**Aviso do material sobre o perfil "mira":** 34% dos rounds dele são na Nuke, contra 17% do corpus
(2,0x a fatia do mapa). Parte do grupo pode ser efeito do mapa, não estilo do jogador. Medido de
novo no modelo reajustado: os mesmos 34%.

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
