# Decisão 36: PRESERVAÇÃO DE DADOS: nenhum `.dem`, nada de `data/interim/` e nenhum backup é apagado sem o Pedro confirmar uma LISTA EXPLÍCITA dos arquivos, com o tamanho de cada um e a prova de que existe outra cópia conferida por sha256

- **ID:** 36
- **Status:** vigente
- **Data:** 2026-09-27
- **Resumo:** Nenhum `.dem`, interim ou backup é apagado sem lista confirmada e cópia por sha256.

## Texto

36. **PRESERVAÇÃO DE DADOS: nenhum `.dem`, nada de `data/interim/` e nenhum
    backup é apagado sem o Pedro confirmar uma LISTA EXPLÍCITA dos arquivos,
    com o tamanho de cada um e a prova de que existe outra cópia conferida por
    sha256** (regra do Pedro, 2026-09-27). "Nada exclusivo" só vale com hash
    conferido arquivo a arquivo -- nunca por nome, caminho, tamanho ou "o git
    tem". Isso vale também para `clean_match.py --confirmar`, `rm -rf` e
    qualquer limpeza de disco.
    POR QUE (o que aconteceu, investigado em 2026-09-27): as demos NÃO sumiram
    na exclusão de `demos/parser-replay-cs2` (173 MB, 2026-09-26). Elas foram
    apagadas antes, em 2026-09-19 02:52, pelo `clean_match` rodado nas 52
    partidas (27,1 GB), depois de o Pedro responder "pode apagar só as demos" a
    uma proposta que dizia que "a partida continua no site normalmente". Era
    verdade para o site e falso para o projeto: a proposta não dizia que
    qualquer propriedade NOVA da demo (foi o que o item 7 precisou:
    `m_vInitialVelocity`, `m_flThrowStrength`, `duck_amount`) passava a ser
    impossível de extrair. A conferência do `clean_match` olhava a integridade
    do PROCESSADO, não o que a demo tinha e o interim não. A match_23 escapou
    porque tinha mudado de pasta. O clone de 173 MB foi checado só POR CAMINHO
    ("0 arquivos que não existem no repo atual"): o histórico dele está no
    bundle da reescrita (HEAD `87913bc` conferido lá), mas se a árvore de
    trabalho tinha mudança não commitada não dá mais para saber -- é o defeito
    que esta regra fecha.
    Backups atuais: "...- BACKUP interim 2026-09-21" e "...- BACKUP interim
    2026-09-27" (interim + o .dem da match_23, `SHA256SUMS.txt` conferido nos
    dois sentidos). Plano de recuperação das demos, sem nada executado:
    `RECUPERACAO_DEMOS.md`.
    **A trava está no código** (`scripts/clean_match.limpa`, 2026-09-27): cada
    arquivo a apagar precisa de uma cópia nas pastas irmãs "<projeto> -
    BACKUP*" com o mesmo sha256, lido NA HORA dos dois lados (lista gravada não
    vale); sem isso `limpa` recusa, diga-se o que falta e onde procurou, mesmo
    chamada direto pelo Python com `confirmar=True` (o caminho de 19/09). Sem
    `confirmar`, só lista arquivo, tamanho, cópia e hash. Testes em
    `tests/test_manifest.py`.
