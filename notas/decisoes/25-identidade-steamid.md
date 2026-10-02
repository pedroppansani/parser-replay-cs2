# Decisão 25: Identidade é o STEAMID; o nome é rótulo de exibição

- **ID:** 25
- **Status:** vigente
- **Data:** 2026-09-20
- **Resumo:** Identidade é o steamid; o nome é rótulo (`metrics/identidade.py`).

## Texto

25. **Identidade é o STEAMID; o nome é rótulo de exibição** (2026-09-20).
    `metrics/identidade.py` é o único lugar que resolve nome: para cada steamid,
    o nick mais frequente no corpus, e todo relatório entre partidas passa por
    ele. Medido nas 52 partidas / 520 jogador-partidas / 116 steamids: **4
    steamids com mais de um nick** (donk/donk666, sh1ro/SH1R0,
    magixx/lilpeepfan-, e um smurf de FACEIT com 4 nicks), registrados em
    `data/reference/nicks_conhecidos.json`. O risco INVERSO -- dois jogadores
    diferentes com o mesmo nome, que não aparece como duplicata e sim como um
    jogador de estatística estranha -- foi procurado e **não existe no corpus
    hoje**; há invariante que falha se aparecer.
    REGISTRO DE UM DIAGNÓSTICO QUE A MEDIÇÃO REFUTOU: a suspeita era que as
    RÉGUAS do corpus (referência de escala do rating, referência dos papéis)
    estivessem tortas por agrupar por nome. Não estavam: elas agregam por
    (partida, steamid), e o nome só viaja junto como coluna. O estrago estava
    nos relatórios ENTRE partidas (IGL, perfis), que agrupavam por nome e
    partiam o donk em dois. Não "conserte" a régua -- ela não tem esse defeito.
