"""Monta o CLAUDE.md curto a partir das notas (reestruturação, 2026-10-02).

Rodado UMA vez, junto com `divide_claude_md.py`. Depois disso o CLAUDE.md é
mantido à mão: regra nova entra com uma linha em "Regras vigentes" e uma nota
em `notas/decisoes/`.

Uso:
    py -3.12 -m pesquisa.monta_claude_md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from pesquisa.divide_claude_md import META  # noqa: E402

LIMITE_BYTES = 15_000

TOPO = """# Contexto do projeto para o Claude Code

Lido no início de cada sessão. Traz só o que está em vigor; o porquê de cada
regra, com o histórico, está em `notas/`.

## O projeto

Parser de replay (.dem) do CS2 que gera um site estático por partida (replay,
leitura da partida, perfil, prancheta tática). O parsing é do `awpy`; **o
diferencial é o desenho das métricas**: cada uma carrega uma decisão de jogo
explícita, e a validação final é o conhecimento de jogo do Pedro (Faceit 10,
flex AWPer). Ao propor ou mudar métrica, a justificativa de JOGO pesa tanto
quanto a corretude.

## Ambiente e como rodar

- Python 3.11 a 3.13 (`py -3.12` no Windows); o awpy 2.0.2 não suporta 3.14.
- O demo é 64 tick; nunca assuma (`metrics/timing.py` detecta).
- `py -3.12 -m pytest tests/` · `py -3.12 -m scripts.reprocessa` (corpus a partir
  do interim) · `py -3.12 -m scripts.build_site` · `py -3.12 -m scripts.escada_validacao`.
- Parse leva ~14 s por partida; itere com `--from-interim`.
- Sem o interim a partida não pode ser recalculada; apagar demo, interim ou
  backup segue a regra 36.

## Mapa do repositório

```
parsing/      wrapper do awpy, versões, verdade do arremesso lida da demo
metrics/      as métricas (uma decisão de jogo por módulo) e as referências .json
clustering/   estilo de jogo por (jogador, round): PCA + KMeans global
scripts/      pipeline, build do site, calibração, manifesto
pesquisa/     scripts de uma vez só (reestruturação desta documentação)
dashboard/web template da página, map_core.js, annotations, tactics (prancheta)
tests/        testes; os de navegador usam Playwright
data/processed  métricas por partida (versionado) · data/lineups  arremessos reais
data/interim    tabelas brutas (fora do git) · demos/  .dem (fora do git)
data/reference  dados oficiais da HLTV · notas/  decisões e investigações
docs/           site gerado (fora do git; o Pages é artefato do CI)
```

## Convenções de código

- Comentários e docstrings em português.
- Toda métrica devolve `(per_round, summary)`; não troque o per_round pelo agregado.
- Limiar é constante nomeada no topo do módulo, com a origem ao lado.
- Polars e Parquet. `group_by` e `unique` sempre com `maintain_order=True`.
- Nada de texto fixo no `template.html` além da estrutura.
- Um commit por passo, com a suíte passando. Meça antes e depois. Teste existente
  não muda sem o Pedro aprovar.

## Regras vigentes

Uma linha por decisão em vigor; o ID é o que o código cita ("decisão 21a"). O
texto completo de cada uma está na nota do link (`notas/decisoes/`).

"""

FIM = """
## Números citáveis

Não cite número de cabeça. Os números do projeto (corpus, rating contra a HLTV,
escada, arremessos, testes) estão em `data/processed/numeros_citaveis.json`,
gerado por `py -3.12 -m scripts.numeros_citaveis`. README e landing leem dali.

## Pontos de calibração que pertencem ao Pedro

Não resolva nenhum destes sozinho; pergunte. Detalhe e histórico de cada um em
[`notas/calibracao.md`](notas/calibracao.md).

- Nomes dos grupos de estilo (`clustering/cluster_names.json`); conferir a cada reajuste.
- Partição A/Mid/B dos mapas (`MANUAL_PLACE_AREAS`); a Nuke é a mais frágil.
- Ângulos de entrada manuais (`MANUAL_ENTRY_ANGLES`).
- Janela de trade (5,0 s) e limiares de peek/hold, contato, pré-fire e rotação.
- Pesos da divisão de crédito do Round Swing e todos os pesos de `round_spectacle.py`.
- Altura dos olhos e diferença em pé/agachado medidas (regra 21c).
- Limiares do card de destaque, do round decisivo, da autópsia e dos papéis.
- Pisos de função (regra 31) e do eixo carrega piano/baiter; repick com mais de uma saída.
- Paleta dos gráficos (regra 10).
- Rota B: força intermediária (0,6141 afirma "médio"), agachamento parcial neutro,
  custo da tabela `movimento`. FACEIT: ligar `TICK_PELO_PROJETIL_SEM_EVENTO`.

## Pendências

- No jogo: [`PENDENCIAS_NO_JOGO.md`](PENDENCIAS_NO_JOGO.md).
- Demos a baixar: [`RECUPERACAO_DEMOS.md`](RECUPERACAO_DEMOS.md).
- Limitações conhecidas: [`notas/limitacoes.md`](notas/limitacoes.md).

## Glossário

- **Gabarito:** arremessos de partidas com `.dem`, com o que a demo grava (força,
  velocidade, postura, chão), em `tests/fixtures/gabarito_arremessos_*`.
- **Rota A:** inferir botão, "no ar" e postura só com posição, pela rotina do jogo medida no gabarito.
- **Rota B:** ler esses valores da demo (parser 2) e declarar a fonte de cada campo.
- **Neutro:** arremesso ou rótulo sem afirmação, com o motivo; nunca um palpite.
- **Catraca:** teste que grava o melhor valor medido e falha se piorar.
- **Fora da amostra:** avaliado em dado que não entrou no ajuste.
- **Regra 36:** preservação de dados (demo, interim e backup).
- Nas notas antigas, "item 7" é a investigação da força do arremesso, "etapa N"
  são as etapas da prancheta e "Fase X" são fases de trabalho anteriores.
"""


def chave(i: str):
    m = re.match(r"(\d+)([a-z]?)", i)
    return (int(m.group(1)), m.group(2))


def regras() -> str:
    linhas = []
    for i in sorted(META, key=chave):
        slug, status, resumo, _ = META[i]
        if status != "vigente":
            continue
        linhas.append(f"- [{i}](notas/decisoes/{i}-{slug}.md) {resumo}")
    return "\n".join(linhas) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    texto = TOPO + regras() + FIM
    (RAIZ / "CLAUDE.md").write_text(texto, encoding="utf-8")
    n = len(texto.encode("utf-8"))
    print(f"CLAUDE.md: {n} bytes ({'dentro' if n <= LIMITE_BYTES else 'ACIMA'} do limite de {LIMITE_BYTES})")


if __name__ == "__main__":
    main()
