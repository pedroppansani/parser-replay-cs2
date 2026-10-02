# Decisão 24: Saída gerada não vai para o repositório

- **ID:** 24
- **Status:** vigente
- **Data:** 2026-09-19
- **Resumo:** Saída gerada (`docs/`) não vai para o repositório; o Pages é artefato do CI.

## Texto

24. **Saída gerada não vai para o repositório.** O que se versiona é o que gera a
    saída (código e `data/processed/`), não a saída. O site em `docs/` era 54% do
    histórico (120 de 224 MB, 24 versões) e foi PURGADO em 2026-09-19 com
    `git filter-repo`, com a concordância do Pedro (repositório nunca
    compartilhado): pacote local 219 -> 96 MB, clone do GitHub com `.git` de 105
    MB. `docs/` está no `.gitignore`, e o Pages é gerado pelo GitHub Actions
    (`.github/workflows/pages.yml`) a partir do código, como artefato -- não
    entra em branch nenhum. Backup de antes da reescrita: a pasta irmã
    "...- BACKUP antes da reescrita 2026-09-19", com `historico-completo.bundle`.
    Teste obrigatório depois de qualquer mudança nisso: clonar do zero, rodar a
    suíte (os testes que dependem de `data/interim/` são PULADOS, nunca
    quebram) e gerar o site só com o que está versionado.
    Peso que continua crescendo, e é deliberado: `replay.json` (50 MB do
    histórico) e `web_payload.json` (16 MB) em `data/processed/`. O replay sai
    do interim, que não é versionado, então sem ele um clone não reconstrói o
    replay.
