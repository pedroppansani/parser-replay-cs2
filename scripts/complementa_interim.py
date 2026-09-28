"""Acrescenta as tabelas da rota B ao interim de uma partida que tem o .dem.

POR QUE COMPLEMENTO, E NÃO REPARSE
----------------------------------
A versão 2 do parser (parsing/versao.py) só ACRESCENTA duas tabelas ao interim
(`arremessos_demo` e `movimento`, parsing/verdade_do_arremesso.py); as tabelas
da versão 1 não mudam. Reparsear do zero regravaria o interim inteiro, e o
interim é dado protegido (decisão 36: nada dele é apagado ou sobrescrito sem a
confirmação do Pedro). O complemento lê da demo SÓ o que é novo e grava
arquivos NOVOS -- recusa se algum deles já existe.

CONFERÊNCIAS (qualquer uma falhando, nada é gravado)
----------------------------------------------------
- o sha256 de cada parte da demo tem de ser o do manifesto: a tabela nova vem
  da MESMA demo que produziu o interim;
- o movimento tem de cobrir 100% das linhas (tick, steamid) da tabela de ticks
  existente, com X, Y, Z idênticos -- é a prova de que os ticks estão
  alinhados, inclusive o deslocamento das partes de uma demo dividida.

Uso:
    py -3.12 -m scripts.complementa_interim match_23 [match_10 ...]
    py -3.12 -m scripts.complementa_interim --todas   # toda partida com .dem e sem complemento
    py -3.12 -m scripts.complementa_interim --ensaio <pasta> match_23   # grava em <pasta>, não no interim
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
from awpy.parsers.rounds import apply_round_num
from demoparser2 import DemoParser

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from parsing import verdade_do_arremesso as va  # noqa: E402
from parsing.parser import TABELAS_DA_VERDADE  # noqa: E402
from parsing.versao import ARQUIVO_DO_COMPLEMENTO, VERSAO_DO_PARSER, versoes  # noqa: E402

INTERIM = RAIZ / "data" / "interim"
# X, Y, Z do movimento contra os da tabela de ticks: o mesmo demoparser lê o
# mesmo campo, então a igualdade é exata; a folga só absorve o float32
FOLGA_POSICAO = 1e-3


def demos_da_partida(partida: str) -> list[Path]:
    """As partes da demo, em ordem (p1, p2...), pelo manifesto; só as que existem."""
    import scripts.manifest as mf
    linha = mf.carrega()["partidas"][partida]
    out = []
    for d in linha["demos"]:
        p = RAIZ / d["caminho"]
        if not p.is_file():
            achados = [q for q in (RAIZ / "demos").rglob(d["arquivo"]) if q.is_file()]
            p = achados[0] if achados else None
        if p is None:
            raise SystemExit(f"{partida}: {d['arquivo']} não está no disco")
        out.append(p)
    return out


def sha256_do_manifesto(partida: str) -> dict[str, str]:
    import scripts.manifest as mf
    return {d["arquivo"]: d.get("sha256") for d in mf.carrega()["partidas"][partida]["demos"]}


def sha256(arq: Path) -> str:
    h = hashlib.sha256()
    with open(arq, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 22), b""):
            h.update(bloco)
    return h.hexdigest()


def deslocamento_da_parte(p: DemoParser, ticks_interim: np.ndarray) -> int:
    """Quanto o interim deslocou os ticks desta parte (parte 1: 0).

    O `merge_interim` soma a cada parte o maior tick das anteriores; o valor
    exato sai casando os ticks do evento grenade_thrown da demo com os do
    interim (a diferença mais frequente). A conferência de X, Y, Z do
    movimento é que prova que o valor está certo.
    """
    ev = p.parse_event("grenade_thrown")
    if ev is None or len(ev) == 0:
        return 0
    cont: Counter = Counter()
    for e in ev["tick"].to_numpy()[:40]:
        for g in ticks_interim:
            if g >= e:
                cont[int(g - e)] += 1
    return int(cont.most_common(1)[0][0])


def complementa(partida: str, saida: Path | None = None) -> dict:
    """Grava arremessos_demo, movimento e o registro. Devolve o registro.

    `saida` grava numa OUTRA pasta (ensaio): lê do interim, não escreve nele.
    """
    pasta = INTERIM / partida
    alvo = pasta if saida is None else Path(saida) / partida
    alvo.mkdir(parents=True, exist_ok=True)
    destinos = [alvo / f"{n}.parquet" for n in TABELAS_DA_VERDADE] + [alvo / ARQUIVO_DO_COMPLEMENTO]
    existentes = [d.name for d in destinos if d.exists()]
    if existentes:
        raise SystemExit(f"{partida}: já existe {existentes} -- o complemento não sobrescreve nada (decisão 36)")

    dems = demos_da_partida(partida)
    esperado = sha256_do_manifesto(partida)
    shas = {}
    for dem in dems:
        s = sha256(dem)
        if esperado.get(dem.name) != s:
            raise SystemExit(f"{partida}: {dem.name} tem sha256 {s[:12]}, o manifesto diz "
                             f"{(esperado.get(dem.name) or '-')[:12]} -- não é a demo que produziu o interim")
        shas[dem.name] = s

    ticks = pl.read_parquet(pasta / "ticks.parquet", columns=["tick", "steamid", "X", "Y", "Z"]).with_columns(
        pl.col("tick").cast(pl.Int32), pl.col("steamid").cast(pl.UInt64))
    ev = pl.read_parquet(pasta / "grenade_thrown.parquet")["tick"].to_numpy() if (pasta / "grenade_thrown.parquet").exists() \
        else ticks["tick"].unique(maintain_order=True).sort().to_numpy()
    arrs, movs, partes, ligacao = [], [], [], Counter()
    lidas = [(dem, DemoParser(str(dem))) for dem in dems]
    desl = [deslocamento_da_parte(p, ev) if len(dems) > 1 else 0 for _, p in lidas]
    for k, (dem, p) in enumerate(lidas):
        t0 = time.time()
        d = desl[k]
        # cada parte cobre [deslocamento dela, deslocamento da próxima): a demo
        # crua de uma parte continua depois do último round (servidor parado),
        # e essa cauda cairia em cima da parte seguinte já deslocada. O interim
        # não a tem -- o `ticks` do awpy só guarda ticks dentro de round.
        fim = desl[k + 1] if k + 1 < len(desl) else None
        na_parte = (pl.col("tick") < fim) if fim is not None else pl.lit(True)
        arr, _ = va.arremessos_demo(p)
        arr = arr.with_columns((pl.col("tick") + d).cast(pl.Int32)).filter(na_parte)
        ligacao.update(dict(arr["ligacao"].value_counts().rows()))
        mov = va.movimento(p)
        base, frac, n = va.base_do_ultimo_pulo(p)
        arrs.append(arr)
        movs.append(mov.with_columns((pl.col("tick") + d).cast(pl.Int32), pl.col("tick_do_ultimo_pulo") + d).filter(na_parte))
        partes.append({"arquivo": dem.name, "sha256": shas[dem.name], "deslocamento_de_tick": d,
                       "base_do_ultimo_pulo": base, "base_confere": round(frac, 5), "decolagens": n,
                       "segundos": round(time.time() - t0, 1)})

    mov = pl.concat(movs)
    duplicadas = mov.group_by("tick", "steamid", maintain_order=True).len().filter(pl.col("len") > 1).height
    if duplicadas:
        raise SystemExit(f"{partida}: {duplicadas} chaves (tick, steamid) repetidas no movimento -- "
                         "as partes se sobrepõem; nada gravado")
    casado = ticks.join(mov.with_columns(pl.lit(True).alias("_par")), on=["tick", "steamid"], how="left", suffix="_d")
    faltam = int(casado["_par"].is_null().sum())
    # posição nula dos DOIS lados (jogador morto) é igual; nula de um lado só, não
    dif = casado.filter(pl.col("_par").is_not_null()).select(
        *[(pl.col(e).is_null() != pl.col(f"{e}_d").is_null()) | ((pl.col(e) - pl.col(f"{e}_d")).abs() > FOLGA_POSICAO)
          for e in "XYZ"])
    fora = int(dif.select(pl.any_horizontal(pl.all().fill_null(False)).alias("d"))["d"].sum())
    if faltam or fora:
        raise SystemExit(f"{partida}: movimento NÃO casa com a tabela de ticks ({faltam} linhas sem par, "
                         f"{fora} com posição diferente em {ticks.height}) -- nada gravado")
    mov = mov.join(ticks.select("tick", "steamid"), on=["tick", "steamid"], how="semi").drop("X", "Y", "Z")

    rounds = pl.read_parquet(pasta / "rounds.parquet")
    arr = pl.concat(arrs)
    arr = apply_round_num(df=arr, rounds_df=rounds, tick_col="tick").filter(pl.col("round_num").is_not_null())

    arr.write_parquet(alvo / "arremessos_demo.parquet")
    va.grava_movimento(mov, alvo / "movimento.parquet")
    registro = {
        "_leia_isto": ("Tabelas da rota B acrescentadas a um interim existente por "
                       "scripts/complementa_interim.py; as outras tabelas não foram tocadas."),
        "versao_do_parser": VERSAO_DO_PARSER,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "codigo": {k: v for k, v in versoes().items() if k in ("commit", "sujo", "demoparser2")},
        "partes": partes,
        "conferencia": {"linhas_de_ticks": ticks.height, "linhas_sem_par": faltam, "posicao_diferente": fora,
                        "chaves_repetidas": duplicadas},
        "projeteis": arr.height,
        "ligacao_da_forca": dict(ligacao),
        "tabelas": {n: round((alvo / f"{n}.parquet").stat().st_size / 1e6, 3) for n in TABELAS_DA_VERDADE},
    }
    (alvo / ARQUIVO_DO_COMPLEMENTO).write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    return registro


def main(args: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    saida = None
    if args[:1] == ["--ensaio"]:
        saida, args = Path(args[1]), args[2:]
    if args == ["--todas"]:
        import scripts.manifest as mf
        args = []
        for partida in sorted(mf.carrega()["partidas"]):
            if (INTERIM / partida / ARQUIVO_DO_COMPLEMENTO).exists() or not (INTERIM / partida).is_dir():
                continue
            try:
                demos_da_partida(partida)
            except (SystemExit, KeyError):
                continue
            args.append(partida)
    for partida in args:
        r = complementa(partida, saida)
        print(f"{partida}: {r['projeteis']} projéteis, ligação {r['ligacao_da_forca']}, "
              f"{r['conferencia']['linhas_de_ticks']} linhas de ticks conferidas, "
              f"partes {[(x['arquivo'], x['deslocamento_de_tick']) for x in r['partes']]}, tabelas {r['tabelas']} MB")


if __name__ == "__main__":
    main(sys.argv[1:])
