"""Importa demos baixadas à mão, identificando cada .dem pelo sha256 do manifesto.

Fluxo (decisão 7 do item 7, 2026-09-27): o Pedro solta os arquivos em
`demos/entrada/`, compactados ou não. Este script:
  1. extrai os pacotes (.rar, .zip, .7z, .gz, ...) para
     `demos/entrada/_extraido/<pacote>/`, sem apagar o pacote;
  2. calcula o sha256 de cada .dem e procura no manifesto -- o NOME não
     identifica demo (decisão 27), o hash sim;
  3. o que bate volta para o caminho registrado no manifesto (dentro de
     `demos/`) e é COPIADO para o backup mais recente, com o hash da cópia
     conferido (decisão 36);
  4. lista o que não bate: hash divergente (mesmo nome de arquivo de uma demo
     do manifesto, conteúdo diferente) e .dem fora do corpus (outros mapas da
     série).
NÃO apaga nada. Pacotes, extraídos e .dem fora do corpus ficam em
`demos/entrada/` até o Pedro confirmar a remoção pelo fluxo da regra 36.

Depois de importar: `py -3.12 -m scripts.manifest` marca as demos como
existentes de novo.

Uso:
    py -3.12 -m scripts.importa_demos              # importa
    py -3.12 -m scripts.importa_demos --simular    # só mostra o que faria
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts import clean_match as cm
from scripts import manifest as mf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRADA = PROJECT_ROOT / "demos" / "entrada"
PACOTES = (".rar", ".zip", ".7z", ".gz", ".bz2", ".zst", ".tar", ".xz")
SETE_ZIP = Path(r"C:\Program Files\7-Zip\7z.exe")


def extrai(pacote: Path, destino: Path) -> str | None:
    """Extrai um pacote. Devolve None se deu certo, ou a mensagem de erro."""
    destino.mkdir(parents=True, exist_ok=True)
    try:
        if pacote.suffix.lower() == ".zip":
            with zipfile.ZipFile(pacote) as z:
                z.extractall(destino)
            return None
    except zipfile.BadZipFile as err:
        return f"zip inválido: {err}"
    r = subprocess.run(["tar", "-xf", str(pacote), "-C", str(destino)], capture_output=True, text=True)
    if r.returncode == 0:
        return None
    if SETE_ZIP.is_file():
        r2 = subprocess.run([str(SETE_ZIP), "x", "-y", f"-o{destino}", str(pacote)], capture_output=True, text=True)
        if r2.returncode == 0:
            return None
        return f"tar: {r.stderr.strip()[:200]} | 7z: {r2.stderr.strip()[:200]}"
    return f"tar: {r.stderr.strip()[:200]}"


def demos_do_manifesto() -> tuple[dict[str, tuple[str, dict]], dict[str, list[str]]]:
    """sha256 -> (match_id, entrada da demo) e nome de arquivo -> match_ids."""
    por_hash, por_nome = {}, {}
    for mid, linha in mf.carrega()["partidas"].items():
        for d in linha.get("demos", []):
            if d.get("sha256"):
                por_hash[d["sha256"]] = (mid, d)
            por_nome.setdefault(d["arquivo"], []).append(mid)
    return por_hash, por_nome


def backup_de_destino() -> Path | None:
    """A pasta demos/ do backup mais recente (as pastas têm a data no nome)."""
    b = cm.pastas_de_backup()
    return (b[-1] / "demos") if b else None


def importa(simular: bool = False, entrada: Path | None = None) -> dict:
    entrada = ENTRADA if entrada is None else entrada
    out = {"extraidos": [], "falhas_de_extracao": [], "importados": [], "ja_no_lugar": [],
           "divergentes": [], "fora_do_corpus": [], "sem_backup": []}
    if not entrada.is_dir():
        return out
    for pacote in sorted(p for p in entrada.iterdir() if p.is_file() and p.suffix.lower() in PACOTES):
        destino = entrada / "_extraido" / pacote.stem
        if destino.is_dir() and any(destino.rglob("*.dem")):
            continue
        if simular:
            out["extraidos"].append(str(pacote))
            continue
        erro = extrai(pacote, destino)
        (out["falhas_de_extracao"] if erro else out["extraidos"]).append(str(pacote) if not erro else f"{pacote.name}: {erro}")

    por_hash, por_nome = demos_do_manifesto()
    backup = backup_de_destino()
    for dem in sorted(entrada.rglob("*.dem")):
        h = cm.sha256(dem)
        if h not in por_hash:
            if dem.name in por_nome:
                out["divergentes"].append({"arquivo": str(dem), "sha256": h, "partidas_com_esse_nome": por_nome[dem.name]})
            else:
                out["fora_do_corpus"].append({"arquivo": str(dem), "sha256": h})
            continue
        mid, d = por_hash[h]
        alvo = PROJECT_ROOT / d["caminho"]
        if alvo.is_file() and cm.sha256(alvo) == h:
            out["ja_no_lugar"].append({"match_id": mid, "arquivo": str(dem)})
            continue
        registro = {"match_id": mid, "de": str(dem), "para": str(alvo), "sha256": h, "bytes": dem.stat().st_size}
        if simular:
            out["importados"].append(registro)
            continue
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dem), str(alvo))
        if backup is None:
            out["sem_backup"].append(registro)
        else:
            copia = backup / alvo.name
            backup.mkdir(parents=True, exist_ok=True)
            if not (copia.is_file() and cm.sha256(copia) == h):
                shutil.copy2(alvo, copia)
            if cm.sha256(copia) != h:
                out["sem_backup"].append({**registro, "erro": "a cópia no backup não conferiu"})
            else:
                registro["copia"] = str(copia)
                somas = backup.parent / "SHA256SUMS.txt"
                with open(somas, "a", encoding="utf-8") as f:
                    f.write(f"{h} *demos/{alvo.name}\n")
        out["importados"].append(registro)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Importa demos de demos/entrada/ pelo sha256 do manifesto.")
    ap.add_argument("--simular", action="store_true", help="só mostra o que faria")
    r = importa(simular=ap.parse_args().simular)
    for chave, titulo in (("extraidos", "pacotes extraídos"), ("falhas_de_extracao", "FALHA NA EXTRAÇÃO"),
                          ("importados", "importados (hash confere com o manifesto)"),
                          ("ja_no_lugar", "já estavam no lugar"), ("divergentes", "HASH DIVERGENTE (não entram)"),
                          ("fora_do_corpus", "fora do corpus (ficam em demos/entrada/)"),
                          ("sem_backup", "SEM CÓPIA NO BACKUP")):
        if r[chave]:
            print(f"{titulo}: {len(r[chave])}")
            for x in r[chave]:
                print(f"    {x}")
    if r["importados"]:
        print("\nPróximo passo: py -3.12 -m scripts.manifest (marca as demos como existentes).")


if __name__ == "__main__":
    main()
