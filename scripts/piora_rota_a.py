"""Piora da biblioteca de arremessos entre duas versões (definição da 21a).

Compara, arremesso a arremesso (pelo id), a biblioteca de uma revisão do git
(`--antes`, padrão `main`) com a de `data/lineups/` no disco:
  - PIORA: tinha o botão X com a velocidade antiga a até TOLERANCIA_BOTAO do
    centro de X e passa a outro botão, ou fica neutro sem regra explícita;
  - CORREÇÃO DE RÓTULO ANTIGO: tinha X com a velocidade antiga FORA da
    tolerância e passa a outro botão dentro dela, por causa identificada
    (regra do pulo, vertical 0 em escada/rampa, janela, pés em t);
  - troca sem causa conta como piora.
Ficar neutro por regra explícita (estado vertical, guarda do voo, tolerância)
não é piora e é contado à parte.

Uso:
    py -3.12 -m scripts.piora_rota_a [--antes main]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics import grenade_throws as gt  # noqa: E402

ROTULO_PARA_BOTAO = {v: k for k, v in gt.ROTULO_DO_BOTAO.items()}
REGRA_OK = ("chão", "regra fixa 6-13", "vz real 19+")


def biblioteca(rev: str | None) -> dict[str, dict]:
    out = {}
    arquivos = sorted((RAIZ / "data/lineups").glob("*.json"))
    for f in arquivos:
        rel = f.relative_to(RAIZ).as_posix()
        texto = (subprocess.run(["git", "show", f"{rev}:{rel}"], capture_output=True, cwd=RAIZ, check=True).stdout.decode("utf-8")
                 if rev else f.read_text(encoding="utf-8"))
        for r in json.loads(texto)["arremessos"]:
            out[r["id"]] = r
    return out


def causa(antes: dict, depois: dict) -> str | None:
    ev = depois.get("estado_vertical")
    if ev == "regra fixa 6-13":
        return "regra do pulo"
    if ev == "vz real 19+":
        return "janela (vz real depois de 19 ticks)"
    if ev == "chão" and antes.get("no_ar"):
        return "vertical 0 em escada/rampa"
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", default="main")
    antes, depois = biblioteca(ap.parse_args().antes), biblioteca(None)
    tol = gt.TOLERANCIA_BOTAO
    por = defaultdict(Counter)
    pioras, correcoes, neutros = [], [], Counter()
    for i, d in depois.items():
        p = d["partida"]
        a = antes.get(i)
        if a is None:
            por[p]["entrou"] += 1
            continue
        la = a.get("forca") if a.get("forca") in ROTULO_PARA_BOTAO else None
        ln = d.get("forca") if d.get("forca") in ROTULO_PARA_BOTAO else None
        if a.get("comando") != d.get("comando"):
            por[p]["comando mudou"] += 1
        if la is None:
            por[p]["ganhou botão" if ln else "neutro antes e depois"] += 1
            continue
        va = a.get("velocidade")
        dentro = va is not None and abs(va - gt.VELOCIDADE_BOTAO[ROTULO_PARA_BOTAO[la]]) <= tol
        if ln == la:
            por[p]["mesmo botão"] += 1
        elif ln is None:
            motivo = d.get("estado_vertical") if d.get("estado_vertical") not in REGRA_OK else "tolerância"
            neutros[motivo] += 1
            por[p]["neutro por regra"] += 1
        else:
            c = causa(a, d)
            dn = abs(d["velocidade"] - gt.VELOCIDADE_BOTAO[ROTULO_PARA_BOTAO[ln]])
            linha = (i, d.get("jogador"), d.get("arma"), la, ln, va, None if va is None else round(abs(va - gt.VELOCIDADE_BOTAO[ROTULO_PARA_BOTAO[la]]), 1),
                     d.get("velocidade"), round(dn, 1), c)
            if dentro or c is None:
                pioras.append(linha)
                por[p]["PIORA"] += 1
            else:
                correcoes.append(linha)
                por[p]["correção de rótulo antigo"] += 1
    for i, a in antes.items():
        if i not in depois:
            por[a["partida"]]["saiu"] += 1
    print(f"tolerância vigente: {tol}")
    print("\npartida    piora  correções  mesmo  ganhou  neutro(regra)  entrou  saiu  comando mudou")
    for p in sorted(por):
        c = por[p]
        print(f"{p}   {c['PIORA']:5d}  {c['correção de rótulo antigo']:9d}  {c['mesmo botão']:5d}  {c['ganhou botão']:6d}  "
              f"{c['neutro por regra']:13d}  {c['entrou']:6d}  {c['saiu']:4d}  {c['comando mudou']:13d}")
    tot = sum((por[p] for p in por), Counter())
    print(f"TOTAL      {tot['PIORA']:5d}  {tot['correção de rótulo antigo']:9d}  {tot['mesmo botão']:5d}  {tot['ganhou botão']:6d}  "
          f"{tot['neutro por regra']:13d}  {tot['entrou']:6d}  {tot['saiu']:4d}  {tot['comando mudou']:13d}")
    print("\nneutros por regra (tinham botão):", dict(neutros))
    print("\nPIORAS (id, jogador, granada, antes, depois, vel. antes, dist. antes, vel. depois, dist. depois, causa):")
    for x in pioras:
        print("  ", x)
    print("\nCORREÇÕES DE RÓTULO ANTIGO (mesmos campos):")
    for x in correcoes:
        print("  ", x)


if __name__ == "__main__":
    main()
