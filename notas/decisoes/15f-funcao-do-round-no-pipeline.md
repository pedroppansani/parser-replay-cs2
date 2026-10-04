# Decisão 15f: REGRESSÃO ACHADA NO CAMINHO (2026-09-24): o pipeline rodava os papéis comportamentais SEM a função do round

- **ID:** 15f
- **Status:** vigente
- **Data:** 2026-09-24
- **Resumo:** O pipeline passa a função do round aos papéis comportamentais (regressão corrigida).

## Texto

15f. **REGRESSÃO ACHADA NO CAMINHO (2026-09-24): o pipeline rodava os papéis
    comportamentais SEM a função do round.** `leitura/insights.py` montava
    o dicionário de saídas sem `structural_roles`, então `funcao_do_round` caía
    em "sem_funcao" para todos os rounds. A decisão 15c valia no ajuste da
    referência (que passa a tabela) e NÃO valia no número que ia para a página --
    as duas escalas eram diferentes, e a isca relativa era, na prática, a isca
    crua. Consertado; há de conferir isso sempre que uma métrica nova depender de
    outra tabela do processado.
