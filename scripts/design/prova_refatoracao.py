"""
Prova de que uma refatoração não mudou nada (cartão 9): o site gerado tem de sair IGUAL BYTE A BYTE.

Compara a revisão `--base` (por padrão o ponto onde o alvo saiu da `origin/main`) com o commit atual (HEAD):

1. o site inteiro (`scripts.build_site`) gerado em dois worktrees limpos, só com o versionado, e o sha256 de CADA
   arquivo de `docs/` (o build é determinístico: duas gerações do mesmo commit dão os mesmos bytes);
2. a impressão dos números (`scripts.design.impressao_numeros`) dos dois `docs/`;
3. os 4 quadros do canvas da `compara_capturas` (replay da Mirage, dois andares da Nuke, prancheta);
4. a `compara_paginas`: as abas da partida, no computador e no celular;
5. com `--suite`, a suíte inteira NESTA pasta (no PC do Pedro, com o `data/interim`, sem os testes pulados).

Qualquer diferença em qualquer item reprova: não existe "quase igual". O relatório e os logs ficam em
`logs/prova_refatoracao/` (fora do git). Com `--branch`, o script antes busca a branch no `origin` e a abre (só
com a árvore limpa); sem ela, prova o HEAD como está. Mudança não commitada reprova: a prova é de commit.

    py -3.12 -m scripts.design.prova_refatoracao
    py -3.12 -m scripts.design.prova_refatoracao --branch cartao-9-passo-3 --suite
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

LIMITE_BUILD_S = 1800         # o build do site leva ~45 s na nuvem; folga para o PC e para disco lento
LIMITE_SUITE_S = 3 * 3600     # a suíte inteira com o data/interim
PARTIDAS_DAS_PAGINAS = ["match_23", "match_02"]   # as da compara_paginas (o padrão dela)


def _git(*args: str, cwd: Path = RAIZ) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _abre_a_branch(branch: str, log) -> None:
    """Busca a branch no origin e a abre; com mudança não commitada, para (nada é descartado)."""
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("há mudança não commitada: commite ou guarde antes de rodar a prova")
    _git("fetch", "origin", branch, "main")
    if _git("rev-parse", "--abbrev-ref", "HEAD") != branch:
        _git("switch", branch)
    _git("merge", "--ff-only", f"origin/{branch}")
    log(f"branch {branch} em {_git('rev-parse', '--short', 'HEAD')}")


def _sha256_da_pasta(pasta: Path) -> dict[str, str]:
    return {p.relative_to(pasta).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(pasta.rglob("*")) if p.is_file()}


def _gera_o_site(rev: str, lado: str, temp: Path, saida: Path) -> Path:
    """O site da revisão `rev` num worktree limpo; devolve a pasta `docs/` (copiada para fora do worktree)."""
    wt = temp / f"wt_{lado}"
    _git("worktree", "add", "--detach", "-q", str(wt), rev)
    try:
        with open(saida / f"build_{lado}.log", "w", encoding="utf-8") as f:
            subprocess.run([sys.executable, "-B", "-m", "scripts.build_site"], cwd=wt, check=True,
                           stdout=f, stderr=subprocess.STDOUT, timeout=LIMITE_BUILD_S)
        docs = temp / f"docs_{lado}"
        shutil.move(str(wt / "docs"), docs)
        return docs
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=RAIZ, check=False)


def prova_do_site(base: str, alvo: str, temp: Path, saida: Path, log) -> tuple[bool, dict[str, Path]]:
    docs = {lado: _gera_o_site(rev, lado, temp, saida) for lado, rev in (("base", base), ("alvo", alvo))}
    h = {lado: _sha256_da_pasta(d) for lado, d in docs.items()}
    for lado in h:
        (saida / f"sha256_{lado}.txt").write_text("".join(f"{v}  {k}\n" for k, v in h[lado].items()),
                                                  encoding="utf-8", newline="\n")
    so_base = sorted(set(h["base"]) - set(h["alvo"]))
    so_alvo = sorted(set(h["alvo"]) - set(h["base"]))
    diferentes = sorted(k for k in set(h["base"]) & set(h["alvo"]) if h["base"][k] != h["alvo"][k])
    ok = not (so_base or so_alvo or diferentes)
    log(f"1. site: {len(h['base'])} arquivos na base, {len(h['alvo'])} no alvo; "
        + ("TODOS IGUAIS byte a byte (sha256)" if ok else
           f"{len(diferentes)} diferente(s), {len(so_base)} só na base, {len(so_alvo)} só no alvo"))
    for rotulo, lista in (("diferente", diferentes), ("só na base", so_base), ("só no alvo", so_alvo)):
        for k in lista:
            log(f"   {rotulo}: {k}")
    return ok, docs


def prova_da_impressao(docs: dict[str, Path], saida: Path, log) -> bool:
    from scripts.design.impressao_numeros import compara, impressao, para_texto
    imp = {lado: impressao(d) for lado, d in docs.items()}
    for lado in imp:
        (saida / f"impressao_{lado}.txt").write_text(para_texto(imp[lado]), encoding="utf-8", newline="\n")
    dif = compara(imp["base"], imp["alvo"])
    novas = sorted(set(imp["alvo"]) - set(imp["base"]))
    ok = not dif and not novas
    log(f"2. impressão dos números: {len(imp['alvo'])} linhas contra {len(imp['base'])}; "
        + ("nenhuma diferença" if ok else f"{len(dif)} diferença(s), {len(novas)} linha(s) nova(s)"))
    for d in (dif + novas)[:50]:
        log(f"   {d}")
    return ok


def prova_dos_quadros(base: str, alvo: str, temp: Path, saida: Path, log) -> bool:
    import scripts.compara_capturas as cc
    pasta = saida / "quadros"
    pasta.mkdir(exist_ok=True)
    pa = cc._gera_paginas(base, temp / "quadros_base", temp)
    pd = cc._gera_paginas(alvo, temp / "quadros_alvo", temp)
    cc._captura(pa, pasta, "antes", "padrao")
    reg = cc._captura(pd, pasta, "depois", "padrao")
    ok = True
    log("3. quadros do canvas (compara_capturas):")
    for nome in [q[0] for q in cc.QUADROS_REPLAY] + [cc.QUADRO_PRANCHETA]:
        r = cc._compara(pasta, nome, reg.get(nome, []), cc.RAIO_VIZINHANCA_PADRAO)
        ok = ok and r == "idêntico"
        log(f"   {nome:24s} {r}")
    return ok


def prova_das_paginas(base: str, saida: Path, log) -> bool:
    """As abas da partida, no computador e no celular; o "depois" é esta pasta (o HEAD, já que a árvore está limpa)."""
    import scripts.compara_paginas as cp
    linhas = cp.compara(PARTIDAS_DAS_PAGINAS, base, saida / "paginas", list(cp.TAMANHOS))
    ok = True
    log("4. páginas (compara_paginas):")
    for l in linhas:
        if l["aba"] == "(página)":
            continue
        ok = ok and l["resultado"] == "idêntico"
        log(f"   {l['partida']} {l['tamanho']:8s} {l['aba']:10s} {l['resultado']}"
            + ("" if l["pixels"] is None else f" ({l['pixels']} px)"))
    return ok


def prova_da_suite(saida: Path, log) -> bool:
    log_suite = saida / "suite.log"
    # o pytest em UTF-8 (no Windows a saída ia na codificação antiga e o resumo caía com UnicodeDecodeError, no PC do
    # Pedro em 2026-10-29), e a leitura troca qualquer byte estranho em vez de cair
    with open(log_suite, "w", encoding="utf-8") as f:
        r = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"],
                           cwd=RAIZ, stdout=f, stderr=subprocess.STDOUT, timeout=LIMITE_SUITE_S,
                           env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    resumo = [l for l in log_suite.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()][-1:]
    log(f"5. suíte: {resumo[0] if resumo else '(sem saída)'} (log em {log_suite})")
    return r.returncode == 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Prova byte a byte de que uma refatoração não mudou o site.")
    ap.add_argument("--base", default="origin/main",
                    help="revisão de comparação; vale o ponto onde o HEAD saiu dela (git merge-base)")
    ap.add_argument("--branch", default=None, help="busca e abre esta branch antes (árvore limpa)")
    ap.add_argument("--suite", action="store_true", help="roda também a suíte inteira nesta pasta")
    ap.add_argument("--saida", type=Path, default=None)
    a = ap.parse_args(argv)

    saida = a.saida or RAIZ / "logs" / "prova_refatoracao" / time.strftime("%Y%m%d-%H%M%S")
    saida.mkdir(parents=True, exist_ok=True)
    relatorio = saida / "relatorio.txt"

    def log(texto: str) -> None:
        print(texto, flush=True)
        with open(relatorio, "a", encoding="utf-8") as f:
            f.write(texto + "\n")

    if a.branch:
        _abre_a_branch(a.branch, log)
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("há mudança não commitada: a prova é de commit; commite antes")
    alvo = _git("rev-parse", "HEAD")
    base = _git("merge-base", alvo, a.base)
    log(f"base {base[:10]} ({a.base}, ponto de saída) x alvo {alvo[:10]} (HEAD) · resultado em {saida}")

    temp = Path(tempfile.mkdtemp(prefix="prova_refatoracao_"))
    resultados = {}
    try:
        resultados["site"], docs = prova_do_site(base, alvo, temp, saida, log)
        resultados["impressão"] = prova_da_impressao(docs, saida, log)
        resultados["quadros"] = prova_dos_quadros(base, alvo, temp, saida, log)
        resultados["páginas"] = prova_das_paginas(base, saida, log)
        if a.suite:
            resultados["suíte"] = prova_da_suite(saida, log)
    finally:
        shutil.rmtree(temp, ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=RAIZ, check=False)
    falhas = [k for k, v in resultados.items() if not v]
    log("RESULTADO: " + ("PASSA (" + ", ".join(resultados) + ")" if not falhas else "FALHA em " + ", ".join(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
