# Decisão 27: Toda partida processada carrega a VERSÃO do código que a produziu

- **ID:** 27
- **Status:** vigente
- **Data:** 2026-09-28
- **Resumo:** Cada partida grava a versão do parser (lida do interim) e das métricas, e o commit.

## O que vale hoje

"51 das 52 sem o .dem" é de 2026-09-20. Hoje 13 partidas têm a demo e o parser 2; 39 não têm (`py -3.12 -m scripts.manifest --versoes`).

## Texto

27. **Toda partida processada carrega a VERSÃO do código que a produziu**
    (`parsing/versao.py` -> `match_meta.json` -> `data/manifest.json`).
    São DUAS versões, e a diferença entre elas é cara:
    `VERSAO_DO_PARSER` cobre o que vira `data/interim/` e refazer **exige o
    .dem**; `VERSAO_DAS_METRICAS` cobre o que vira `data/processed/` e refazer
    custa um `--from-interim`. Sobe quem muda NÚMERO, com uma linha de histórico
    no módulo (há teste que falha se a versão subir sem o registro).
    Junto vai o COMMIT do git, porque versão declarada à mão não pega quem
    esqueceu de subi-la -- a versão decide o que reprocessar, o commit audita
    depois. O campo `sujo` marca processamento feito com mudança não commitada:
    ali o commit registrado não descreve inteiramente aquele número.
    **A versão do PARSER é a do INTERIM, não a do código** (2026-09-28): um
    `--from-interim` lê `versao_do_parser` do `complemento_rota_b.json` ou do
    `header.json` (parse novo grava ali); sem registro, mantém a que já estava
    no match_meta, e sem nenhuma, `None` (desconhecida). Antes disso, subir
    `VERSAO_DO_PARSER` faria as partidas sem .dem se declararem "parser novo"
    no primeiro reprocessamento.
    `py -3.12 -m scripts.manifest --versoes` separa o trabalho em três:
    refazer com `--from-interim`, reparsear (demo no disco) e **SEM DEMO**.
    Partida sem versão registrada entra como "desconhecida", não como velha:
    "não sei" virar "está velho" faria o relatório mandar reprocessar o corpus
    inteiro por precaução, que é o mesmo que não relatar nada.
    **MEDIDO E INCÔMODO (2026-09-20): das 52 partidas, 51 não têm mais o .dem no
    disco.** Se `VERSAO_DO_PARSER` subir, elas não podem ser reparseadas -- o
    interim é a única cópia, e o interim NÃO é versionado (fica só nesta
    máquina). Isso é para decidir ANTES de subir a versão do parser, não depois.
    A 52ª (match_23) estava marcada como apagada e não estava: tinha mudado de
    pasta. O manifesto agora reencontra a demo pelo nome **conferindo o
    sha256** (nome de arquivo não identifica demo) e anota o caminho anterior.
