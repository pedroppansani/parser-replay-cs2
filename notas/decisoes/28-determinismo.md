# Decisão 28: O processamento é DETERMINÍSTICO, e o paralelo é aceito só por identidade

- **ID:** 28
- **Status:** vigente
- **Data:** 2026-09-21
- **Resumo:** Processamento determinístico: `group_by`/`unique` com ordem; empate de função por 1 round.

## O que vale hoje

**Um sorteio ficou duas semanas no repositório (achado em 2026-10-02).** A tabela de economia do
rating (`metrics/economia_reference.json`) foi gravada em 2026-09-19, quando o empate da classe de
equipamento do time era desempatado pela ordem de hash. A correção de determinismo de 2026-09-21
tornou o CÓDIGO determinístico, mas as referências globais não são reajustadas por padrão, e o
arquivo antigo continuou em uso. O erro do rating citado (0,079) vinha desse sorteio; ver a decisão
8i para os números.

Por que os testes não pegaram: `tests/test_determinismo.py` trava a causa no código-fonte
(`group_by` e `unique` com ordem, `mode` com `sort`) e roda no mesmo processo, onde a ordem de hash
é fixa; e nenhum teste conferia que um arquivo de referência gravado é o que o código produz.

A brecha foi fechada com dois testes:
- `tests/test_determinismo_em_processos.py`: o cálculo de uma partida inteira e o da tabela de
  economia rodam em dois processos com `PYTHONHASHSEED` diferente e são comparados byte a byte;
- `tests/test_economia_reprodutivel.py`: regerar a tabela de economia do corpus dá exatamente o
  arquivo gravado, que passa a guardar a regra de desempate e o commit que o gerou.

A varredura do código inteiro (aleatoriedade sem semente, `mode` sem ordenação, iteração sobre
`set` cujo resultado dependa da ordem, KMeans e PCA sem semente) não achou outro ponto: KMeans, PCA
e o sorteio de `pesquisa/casos_repick.py` têm semente fixa, e a única iteração sobre `set`
(`scripts/escada_validacao.py`) só preenche um dicionário.

## Texto

28. **O processamento é DETERMINÍSTICO, e o paralelo é aceito só por
    identidade** (2026-09-21). Critério do Pedro: tempo não é o gargalo,
    confiança no número é -- qualquer diferença entre execuções é bug até prova
    em contrário, inclusive ordem de linha e último bit de float.
    O QUE A MEDIÇÃO MOSTROU: antes de paralelizar qualquer coisa, duas execuções
    SEQUENCIAIS das mesmas 3 partidas diferiam em 38 arquivos. O paralelo não
    criava diferença; herdava. Causa: `group_by` e `unique` do Polars devolvem
    os grupos em ordem de HASH, que muda a cada processo (158 `group_by` e 37
    `unique` sem ordem declarada). A ordem não ficava na ordem: vazava para valor
    sempre que alguém cortava ou desempatava depois -- o card de estilo mostrava
    PerdYYY numa execução e chiefkeef19 na outra (empate no 3º lugar com
    `.head(3)`), `unique(subset=)` com `keep="any"` escolhia qualquer linha
    duplicada (a área do jogador em site_roles), `mode().first()` desempatava ao
    acaso (a classe de economia do jogador no rating), e somas em outra ordem
    mudavam o último bit. Pela mesma causa, a SEMENTE FIXA do KMeans não
    garantia resultado: ela vale para a mesma ordem de linhas.
    Correção explícita no código, nada de remendo global na biblioteca: todo
    `group_by`/`unique` com `maintain_order=True`, `unique` com subset com
    `keep="first"`, `mode().sort().first()`, e empate no corte do card entra
    inteiro. `tests/test_determinismo.py` varre o código e falha se aparecer um
    `group_by` sem ordem.
    Aceitação, sem tolerância nenhuma (só o carimbo `processado_em` fica fora):
    3 partidas seq x seq, par x par e seq x par: 141/141 idênticos; **corpus
    inteiro, seq x par e par x par: 2.395/2.395 arquivos idênticos**.
    `scripts/reprocessa.py` refaz o corpus a partir do interim na ordem das
    dependências (métricas -> [referências, só com flag] -> insights -> perfis
    acumulados -> payload -> manifesto), com barreira entre as etapas.
    Medido: sequencial 5 min 35 s; 6 processos 2 min 16 s. Memória com 6
    processos: pico de 9,3 GB acima do início, maior processo 2,36 GB
    (`MEMORIA_POR_PROCESSO_GB` = 2,5). O número de processos sai da memória
    livre e dos núcleos, e é configurável: `PROCESSOS` no módulo ou
    `--processos` na linha de comando; `--sequencial` roda num processo só.
    Referências globais NÃO são reajustadas por padrão (reajustar é decisão);
    os pesos do rating nunca são refeitos ali.
    REPROCESSAMENTO DO CORPUS (etapa 5, 2026-09-21), contra o que estava
    commitado: rating idêntico nos 520 jogador-partidas (erro contra o oficial
    0,077, correlação 0,967, média 1,0720 contra 1,0726 -- tudo igual), round
    decisivo idêntico nas 52, eixo carrega piano/baiter sem mudança, escada de
    validação idêntica. Mudaram 3 de 1.040 funções estruturais dominantes, as três
    de TR para lurker (match_44 flameZ e molodoy, match_51 xertioN). PROVADO que
    eram cara ou coroa: o código de antes da etapa 4, rodado 5 vezes na mesma
    entrada, deu flameZ entry 4x/lurker 1x, molodoy suporte 3x/lurker 2x,
    xertioN entry 4x/lurker 1x. Nos três, a "dominante" é um EMPATE de 4 vias
    com 1 round cada, desempatado pela pontuação média -- que variava porque
    vinha de `.first()` sobre grupos em ordem de hash. Agora é reprodutível.
    EMPATE NA FUNÇÃO DOMINANTE (decisão do Pedro, 2026-09-22): a mesma regra do
    round decisivo e do card de destaque -- proximidade dentro do ruído é empate
    declarado. `structural_roles.MARGEM_EMPATE_FUNCAO_ROUNDS` = 0 (só empate
    exato, o único valor sem parâmetro livre); no empate a função fica nula, as
    empatadas vão junto e o texto sai do Python ("sem função dominante: AWPer
    50% (6 de 12) vs Coringa 50% (6 de 12)"). A margem é em ROUNDS: com ~12 por
    lado, 1 round = 8,3 p.p., e qualquer limiar menor é o empate exato. Curva em
    1.031 jogador-lados: 0 round 145 (14%), 1 round 372 (36%), < 1 desvio do
    ruído 438 (42%), 2 rounds 520 (50%) -- sem patamar; estender é do Pedro.
    Efeito medido: 145 jogador-lados sem função dominante, rating e escada
    idênticos, 3 cards de MVP passaram a declarar o empate. O card do MVP usa o
    lado mais forte INCLUINDO o empate: antes caía para o outro lado, e o ZywOo
    (match_47) aparecia como "Trader, 3 de 8".
    ACHADO PARA O PEDRO: 30 dos 145 empates têm o AWPer entre as empatadas
    (ZywOo 6x6, w0nderful 6x6 de CT). AWPer é função de EQUIPAMENTO disputando
    a contagem com funções de POSIÇÃO -- nos rounds sem AWP (eco, força) o
    jogador recebe uma função posicional. Não é ruído de amostra, é uma
    categoria competindo com outra. Se o AWPer deve vencer o empate por
    prioridade (como já vence em `player_roles.TRAIT_SPECS`) é decisão dele.
    As 52 partidas registram `parser 1, métricas 2`, o commit `56742b2` e
    `sujo: false`; o manifesto passou de 52 "desconhecidas" para 52 em dia.
    **REGRA DE EMPATE ATUAL (convenção do Pedro, 2026-09-27; substitui a margem
    0 acima)**, na ordem de aplicação, que está também no código
    (`structural_roles.MARGEM_EMPATE_FUNCAO_ROUNDS` e `FUNCAO_QUE_VENCE_EMPATE`):
    1. as duas funções com mais rounds naquele lado;
    2. diferença de até **1 round** é empate (entram todas a até 1 round da
       primeira). Medido nas 52: 1 round marca 352 jogador-lados (34,1%); "menos
       de 1 desvio do ruído" marcaria 438 (42,5%). Fica 1 round: dá para explicar
       na tela, não depende de modelo de ruído, e o outro apagaria a função de
       quase metade dos jogador-lados;
    3. no empate, o **AWPer vence -- só se for o AWPer do TIME na partida**, pela
       definição do `player_roles` (piso de `awp_share`, liderança no time,
       amostra mínima). Posse de AWP é sinal mecânico, mais confiável que função
       de posição; quem empata em "AWPer" por pegar a AWP em 2 ou 3 rounds não
       tem esse sinal. O resumo por lado é refeito no `process_demo` DEPOIS do
       `player_roles`, com o conjunto dos AWPers dele: contradição impossível por
       construção (medido: 0);
    4. empate que o passo 3 não resolve é "sem função dominante", com as
       funções empatadas e as contagens.
    Resultado nas 52 (1.031 jogador-lados): **301 sem função dominante
    (29,2%)**; 51 empates vencidos pelo AWPer do time. Dos 30 empates exatos
    originais com o AWPer: 19 o AWPer vence, 11 viram "sem função dominante"
    (FalleN x2, Jimpphat, KSCERATO, Magnojezzz, NiKo, apEX, b1t, kyousuke,
    m0NESY na match_29, ropz -- nenhum é o AWPer do time naquela partida).
