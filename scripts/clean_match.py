"""
Apaga a demo e os dados crus de uma partida, SÓ depois de conferir que o
processado dela está íntegro, e registra a limpeza no manifesto.

Sem --confirmar, não apaga nada: mostra o que conferiu e o que apagaria.

O QUE SE PERDE AO APAGAR O data/interim/
----------------------------------------
Os dados crus (ticks, kills, danos) são a entrada de tudo que RECALCULA uma
partida: process_demo --from-interim, build_insights, build_breakdown,
export_replay e as calibrações (fit_rating, fit_archetype_reference). Depois
da limpeza, a partida continua no site exatamente como está, mas mudança de
métrica ou de texto não chega mais nela, e ela sai da recalibração do rating
-- a menos que a demo seja baixada de novo (o manifesto guarda o hash e o link
da HLTV para isso). O interim pesa ~15MB por partida contra 200-500MB da demo.
Por isso o PADRÃO é apagar só a demo (decisão do Pedro); --apagar-interim
apaga os dois.

TRAVA DA REGRA 36 (decisão 36 do CLAUDE.md)
--------------------------------------------
Nenhum arquivo é apagado sem uma CÓPIA FORA DO PROJETO com o mesmo sha256,
conferido NA HORA da chamada, lendo os dois arquivos (uma lista de hashes
gravada antes pode estar velha, e a cópia pode ter mudado ou sumido). As cópias
são procuradas nas pastas irmãs "<projeto> - BACKUP*". A trava vive dentro de
`limpa`, não na linha de comando: em 2026-09-19 as 52 demos foram apagadas
chamando `limpa` direto pelo Python. Sem --confirmar, a limpeza só lista cada
arquivo com tamanho, onde está a cópia e o hash, e espera a confirmação.

Uso:
    py -3.12 -m scripts.clean_match match_43                    # só confere
    py -3.12 -m scripts.clean_match match_43 --confirmar        # apaga a demo
    py -3.12 -m scripts.clean_match match_43 --confirmar --apagar-interim
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import polars as pl

from metrics.sides import placar_valido
from scripts import manifest as mf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# O que o site e o dashboard leem de uma partida. Sem qualquer um destes, a
# página não se regenera -- e depois da limpeza não há de onde refazê-lo.
ARQUIVOS_OBRIGATORIOS = (
    "match_meta.json",
    "insights.json",
    "web_payload.json",
    "replay.json",
    "breakdown.json",
    "rounds.parquet",
    "adr_summary.parquet",
    "kast_summary.parquet",
)


def verifica(match_id: str) -> list[str]:
    """Problemas que impedem a limpeza. Lista vazia = pode apagar.

    Junta TODOS os problemas em vez de parar no primeiro: quem vai apagar dado
    quer a lista inteira antes de decidir.
    """
    d = PROCESSED_DIR / match_id
    if not d.is_dir():
        return [f"{match_id} não existe em data/processed/"]
    problemas = []

    for nome in ARQUIVOS_OBRIGATORIOS:
        if not (d / nome).is_file():
            problemas.append(f"falta {nome}")

    for p in sorted(d.glob("*.parquet")):
        try:
            pl.read_parquet(p)
        except Exception as err:
            problemas.append(f"{p.name} não abre: {err}")
    lidos = {}
    for p in sorted(d.glob("*.json")):
        try:
            lidos[p.name] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as err:
            problemas.append(f"{p.name} não abre: {err}")

    if {"match_meta.json", "insights.json"} <= lidos.keys() and (d / "rounds.parquet").is_file():
        n = pl.read_parquet(d / "rounds.parquet").height
        meta_n = lidos["match_meta.json"].get("n_rounds")
        partida = lidos["insights.json"].get("match", {})
        a, b = partida.get("score_a"), partida.get("score_b")
        if meta_n != n:
            problemas.append(f"match_meta diz {meta_n} rounds, rounds.parquet tem {n}")
        if a is None or b is None or not placar_valido(a, b, n):
            problemas.append(f"placar impossível: {a}-{b} em {n} rounds")
        replay = lidos.get("replay.json", {})
        if "rounds" in replay and len(replay["rounds"]) != n:
            problemas.append(f"replay.json tem {len(replay['rounds'])} rounds, a partida tem {n}")

    # A identidade da demo tem que estar registrada ANTES de ela sumir.
    linha = mf.carrega()["partidas"].get(match_id)
    if linha is None:
        problemas.append("partida fora do manifesto: rode `py -3.12 -m scripts.manifest` antes")
    else:
        for x in linha.get("demos", []):
            if x.get("existe", True) and not x.get("sha256"):
                problemas.append(f"manifesto sem hash de {x.get('arquivo')}")

    # A página tem que se regenerar só com o processado.
    if not problemas:
        try:
            from scripts.build_web_page import build_html

            build_html(match_id)
        except Exception as err:
            problemas.append(f"a página não se regenera sem o interim: {err}")
    return problemas


def _alvos(match_id: str, manter_interim: bool) -> list[Path]:
    linha = mf.carrega()["partidas"].get(match_id, {})
    alvos = [mf.PROJECT_ROOT / x["caminho"] for x in linha.get("demos", [])
             if (mf.PROJECT_ROOT / x["caminho"]).is_file()]
    interim = INTERIM_DIR / match_id
    if not manter_interim and interim.is_dir():
        alvos.append(interim)
    return alvos


def pastas_de_backup() -> list[Path]:
    """Onde as cópias são procuradas: as pastas irmãs "<projeto> - BACKUP*"."""
    return sorted(p for p in PROJECT_ROOT.parent.glob(PROJECT_ROOT.name + " - BACKUP*") if p.is_dir())


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _arquivos(alvos: list[Path]) -> list[Path]:
    """Os arquivos um a um (uma pasta do interim vira os arquivos dela)."""
    out = []
    for p in alvos:
        out += sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p]
    return out


def copia_conferida(arquivo: Path, backups: list[Path]) -> tuple[dict | None, list[str]]:
    """A cópia fora do projeto com o mesmo sha256, conferida agora lendo os dois.

    Devolve ({arquivo, bytes, sha256, copia}, []) ou (None, [o que faltou]).
    Candidatas: arquivos de mesmo nome e mesmo tamanho dentro das pastas de
    backup; o que decide é o hash, não o nome.
    """
    if not backups:
        return None, [f"{arquivo.name}: nenhuma pasta de backup encontrada ao lado do projeto"]
    tamanho = arquivo.stat().st_size
    candidatas = [q for b in backups for q in b.rglob(arquivo.name) if q.is_file() and q.stat().st_size == tamanho]
    if not candidatas:
        return None, [f"{arquivo.name}: sem cópia de mesmo nome e tamanho em {', '.join(str(b) for b in backups)}"]
    h = sha256(arquivo)
    for q in candidatas:
        if sha256(q) == h:
            return {"arquivo": str(arquivo), "bytes": tamanho, "sha256": h, "copia": str(q)}, []
    return None, [f"{arquivo.name}: {len(candidatas)} cópia(s) com hash DIVERGENTE ({', '.join(str(q) for q in candidatas)})"]


def _tamanho(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def limpa(match_id: str, confirmar: bool = False, manter_interim: bool = True) -> dict:
    """Confere e, com `confirmar`, apaga. Devolve o que foi (ou seria) feito.

    Recusa (ok False, nada apagado) se o processado não está íntegro OU se
    algum arquivo a apagar não tem cópia fora do projeto com o sha256
    conferido agora. `lista` traz, por arquivo: tamanho, onde está a cópia e o
    hash -- é o que a pessoa confirma.
    """
    problemas = verifica(match_id)
    if problemas:
        return {"ok": False, "problemas": problemas, "removidos": [], "bytes": 0, "lista": []}
    alvos = _alvos(match_id, manter_interim)
    backups = pastas_de_backup()
    lista, sem_copia = [], []
    for arq in _arquivos(alvos):
        conferida, faltas = copia_conferida(arq, backups)
        if conferida is None:
            sem_copia += faltas
        else:
            lista.append(conferida)
    if sem_copia:
        return {"ok": False, "problemas": ["regra 36: sem cópia conferida por sha256 -- nada foi apagado"] + sem_copia,
                "removidos": [], "bytes": 0, "lista": lista}
    total = sum(_tamanho(p) for p in alvos)
    if not confirmar:
        return {"ok": True, "simulado": True, "removidos": [str(p) for p in alvos], "bytes": total, "lista": lista}
    for p in alvos:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    mf.registra_limpeza(match_id, alvos, total)
    return {"ok": True, "simulado": False, "removidos": [str(p) for p in alvos], "bytes": total, "lista": lista}


def main() -> None:
    ap = argparse.ArgumentParser(description="Apaga demo e interim de uma partida já processada.")
    ap.add_argument("match_ids", nargs="+")
    ap.add_argument("--confirmar", action="store_true", help="apaga de verdade (sem isto, só confere)")
    ap.add_argument("--apagar-interim", action="store_true",
                    help="apaga também os dados crus: a partida deixa de ser recalculável")
    args = ap.parse_args()
    for mid in args.match_ids:
        r = limpa(mid, args.confirmar, manter_interim=not args.apagar_interim)
        if not r["ok"]:
            print(f"[{mid}] NÃO LIMPA:")
            for p in r["problemas"]:
                print(f"    - {p}")
            continue
        verbo = "apagaria" if r["simulado"] else "apagou"
        print(f"[{mid}] íntegro e com cópia conferida; {verbo} {r['bytes'] / 1e6:.0f}MB:")
        for x in r["lista"]:
            print(f"    - {mf.relativo(x['arquivo'])}  {x['bytes'] / 1e6:.1f}MB  sha256 {x['sha256'][:16]}  cópia: {x['copia']}")
        if r["simulado"]:
            print("    (simulação: rode de novo com --confirmar para apagar)")


if __name__ == "__main__":
    main()
