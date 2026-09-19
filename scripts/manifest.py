"""
Manifesto das partidas: de onde veio cada match_XX, em arquivo versionado.

POR QUE EXISTE
--------------
As demos pesam 200-400MB, não vão para o git e são apagadas depois do
processamento. Sem registro, daqui a um mês existe um match_07 em
data/processed/ e ninguém sabe que partida é -- e a validação do rating contra
a HLTV (que precisa saber QUAL partida é cada match) fica impossível de refazer.

O manifesto (`data/manifest.json`) guarda, por partida: times, evento, mapa,
placar, link da HLTV, hash do arquivo .dem, data de processamento e o registro
da limpeza (scripts/clean_match.py).

O QUE A DEMO NÃO TEM, E COMO ISSO APARECE
-----------------------------------------
- Nome dos times: está na demo (`team_clan_name` de cada jogador) e é lido
  dela. Partida de FACEIT costuma vir sem -- fica null.
- Data da partida: NÃO está no cabeçalho da demo. O que existe é a data de
  modificação do arquivo, que costuma ser a hora em que o GOTV terminou de
  gravar (e sobrevive à extração do zip). Ela vai no campo `data` com a
  procedência escrita ao lado, e não como data conferida.
- Link da HLTV: só quando o ID foi conferido (data/reference/hltv_ratings.json).
  Um ID chutado apontaria para outra partida e contaminaria a validação.

Uso:
    py -3.12 -m scripts.manifest            # atualiza todas as partidas
    py -3.12 -m scripts.manifest match_43   # só algumas
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MANIFEST_FILE = PROJECT_ROOT / "data" / "manifest.json"
HLTV_FILE = PROJECT_ROOT / "data" / "reference" / "hltv_ratings.json"

# Versão do formato do manifesto. Sobe quando um campo muda de sentido.
FORMATO = 1

FONTE_DA_DATA = (
    "data de modificação do arquivo .dem (costuma ser o fim da gravação do GOTV); "
    "não conferida na HLTV"
)

_BLOCO_HASH = 8 * 1024 * 1024


def carrega() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {
        "_leia_isto": (
            "Registro de origem de cada partida processada. Atualizado por "
            "scripts/manifest.py e scripts/process_all_demos.py; a limpeza é "
            "registrada por scripts/clean_match.py."
        ),
        "formato": FORMATO,
        "partidas": {},
    }


def salva(manifesto: dict) -> Path:
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    manifesto["partidas"] = dict(sorted(manifesto["partidas"].items()))
    MANIFEST_FILE.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return MANIFEST_FILE


def relativo(caminho: str | Path) -> str:
    """Caminho relativo ao projeto, com barra normal. O manifesto é versionado:
    não pode carregar o caminho absoluto da máquina de quem processou."""
    p = Path(caminho)
    try:
        return p.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def sha256_do_arquivo(caminho: Path) -> str:
    """Hash do arquivo INTEIRO. A impressão digital de process_all_demos lê só
    as pontas (é para deduplicar rápido); aqui é identidade para sempre."""
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(_BLOCO_HASH), b""):
            h.update(bloco)
    return h.hexdigest()


def _demo(caminho: Path, anterior: dict | None) -> dict:
    """Registro de um arquivo .dem. O hash de 300MB só é recalculado quando o
    arquivo mudou (tamanho ou data), e sobrevive ao arquivo ter sido apagado."""
    info = {"arquivo": caminho.name, "caminho": relativo(caminho)}
    if not caminho.is_file():
        # já apagado pela limpeza: mantém o que foi medido quando existia
        return {**(anterior or {}), **info, "existe": False}
    st = caminho.stat()
    mesmo = anterior and anterior.get("bytes") == st.st_size and anterior.get("mtime") == int(st.st_mtime)
    return {
        **info,
        "existe": True,
        "bytes": st.st_size,
        "mtime": int(st.st_mtime),
        "sha256": anterior["sha256"] if mesmo and anterior.get("sha256") else sha256_do_arquivo(caminho),
    }


def nomes_dos_times(dem: Path, team_of: dict[int, str], tick: int) -> dict[str, str | None]:
    """Nome de cada time (A = começou de TR), lido da própria demo.

    O nome acompanha o time (a entidade), não o lado: lido em qualquer tick,
    cada jogador aparece com o nome do time dele. O tick usado é o fim do freeze
    time do primeiro round jogado, fora do warmup e do round de faca.
    """
    out: dict[str, str | None] = {"A": None, "B": None}
    if not dem.is_file():
        return out
    try:
        from demoparser2 import DemoParser

        df = DemoParser(str(dem)).parse_ticks(["team_clan_name"], ticks=[tick])
    except Exception:
        return out
    votos: dict[str, dict[str, int]] = {"A": {}, "B": {}}
    for sid, nome in zip(df["steamid"], df["team_clan_name"]):
        time_ = team_of.get(int(sid))
        if time_ and nome:
            votos[time_][nome] = votos[time_].get(nome, 0) + 1
    for t, v in votos.items():
        if v:
            out[t] = max(v, key=v.get)
    return out


def _hltv_por_partida() -> dict:
    if not HLTV_FILE.exists():
        return {}
    return json.loads(HLTV_FILE.read_text(encoding="utf-8")).get("partidas", {})


def entrada(match_id: str, anterior: dict | None = None) -> dict:
    """A linha do manifesto de uma partida, a partir do que já está processado."""
    from scripts.fit_rating import identifica_origem

    anterior = anterior or {}
    d = PROCESSED_DIR / match_id
    meta = json.loads((d / "match_meta.json").read_text(encoding="utf-8"))
    partida = json.loads((d / "insights.json").read_text(encoding="utf-8"))["match"]

    fontes = [Path(p) for p in (meta.get("source_parts") or [meta.get("source_dem", "")]) if p]
    demos_ant = {x.get("caminho"): x for x in anterior.get("demos", [])}
    demos = [_demo(f, demos_ant.get(relativo(f))) for f in fontes]

    origem = identifica_origem(meta.get("source_dem", ""))
    faceit = origem["motivo"] is not None and "FACEIT" in origem["motivo"]

    # nomes dos times: lidos uma vez; a demo pode não existir mais depois
    times_ant = anterior.get("times") or {}
    if times_ant.get("A", {}).get("nome") or times_ant.get("B", {}).get("nome"):
        nomes = {t: times_ant.get(t, {}).get("nome") for t in ("A", "B")}
    else:
        import polars as pl

        from scripts.build_insights import resolve_teams

        interim_ticks = PROJECT_ROOT / "data" / "interim" / match_id / "ticks.parquet"
        team_of = {}
        if interim_ticks.exists():
            team_of, _ = resolve_teams(
                pl.read_parquet(interim_ticks, columns=["round_num", "tick", "steamid", "name", "side"])
            )
        r1 = pl.read_parquet(d / "rounds.parquet").sort("round_num").row(0, named=True)
        nomes = (nomes_dos_times(fontes[0], team_of, int(r1["freeze_end"]))
                 if fontes else {"A": None, "B": None})

    hltv = _hltv_por_partida().get(match_id, {})
    hltv_id = hltv.get("hltv_match_id")
    confronto = hltv.get("confronto") or origem["confronto"]

    mtimes = [x["mtime"] for x in demos if x.get("mtime")]
    data = (dt.datetime.fromtimestamp(max(mtimes)).strftime("%Y-%m-%dT%H:%M")
            if mtimes else anterior.get("data"))

    return {
        "match_id": match_id,
        "mapa": meta.get("map_name"),
        "placar": {"A": partida["score_a"], "B": partida["score_b"]},
        "rounds": meta.get("n_rounds"),
        "times": {
            "A": {"nome": nomes["A"], "jogadores": partida["rosters"]["A"], "comecou_de": "t"},
            "B": {"nome": nomes["B"], "jogadores": partida["rosters"]["B"], "comecou_de": "ct"},
        },
        "origem": "faceit" if faceit else "profissional",
        "evento": hltv.get("evento") or origem["evento"],
        "confronto": confronto,
        "mapa_da_serie": hltv.get("mapa_da_serie") or origem["mapa_da_serie"],
        "data": data,
        "fonte_da_data": FONTE_DA_DATA if data else None,
        "hltv": (
            {"match_id": hltv_id,
             "url": f"https://www.hltv.org/matches/{hltv_id}/{confronto or 'partida'}"}
            if hltv_id else None
        ),
        "demos": demos,
        "processado_em": dt.datetime.fromtimestamp(
            os.path.getmtime(d / "match_meta.json")).strftime("%Y-%m-%dT%H:%M"),
        "limpeza": anterior.get("limpeza"),
    }


def atualiza(match_ids: list[str] | None = None) -> dict:
    manifesto = carrega()
    ids = match_ids or sorted(p.name for p in PROCESSED_DIR.glob("match_*") if p.is_dir())
    for mid in ids:
        manifesto["partidas"][mid] = entrada(mid, manifesto["partidas"].get(mid))
    salva(manifesto)
    return manifesto


def registra_limpeza(match_id: str, removidos: list[str], bytes_liberados: int) -> None:
    manifesto = carrega()
    linha = manifesto["partidas"].get(match_id)
    if linha is None:
        raise KeyError(f"{match_id} não está no manifesto: rode scripts.manifest antes de limpar")
    linha["limpeza"] = {
        "em": dt.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "removidos": [relativo(r) for r in removidos],
        "bytes_liberados": bytes_liberados,
    }
    for x in linha.get("demos", []):
        if x.get("caminho") in linha["limpeza"]["removidos"]:
            x["existe"] = False
    salva(manifesto)


def main() -> None:
    ap = argparse.ArgumentParser(description="Atualiza data/manifest.json.")
    ap.add_argument("match_ids", nargs="*", help="partidas (padrão: todas)")
    args = ap.parse_args()
    m = atualiza(args.match_ids or None)
    p = m["partidas"]
    sem_nome = [k for k, v in p.items() if not (v["times"]["A"]["nome"] and v["times"]["B"]["nome"])]
    sem_hltv = [k for k, v in p.items() if v["origem"] == "profissional" and not v["hltv"]]
    print(f"{MANIFEST_FILE}: {len(p)} partidas")
    print(f"  sem nome de time na demo: {len(sem_nome)}")
    print(f"  profissionais sem link da HLTV conferido: {len(sem_hltv)}")


if __name__ == "__main__":
    main()
