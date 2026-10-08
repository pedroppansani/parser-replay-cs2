"""Impressão digital dos números das páginas geradas (guarda dos números das fases design-*).

As fases da direção "Sala de demo" não mudam número nenhum: só forma, cor, tipografia e
estrutura. Este script prova isso. Ele extrai de cada página de `docs/` e do
`data/processed/numeros_citaveis.json` TODO valor numérico do dado embutido e grava um arquivo
ordenado `caminho = valor`; a impressão do main antes do design está em
`notas/design/impressao_antes.txt`, e cada fase compara a dela com ela.

    py -3.12 -m scripts.build_site                                   # regenera docs/
    py -3.12 -m scripts.design.impressao_numeros --grava ARQUIVO     # grava a impressão
    py -3.12 -m scripts.design.impressao_numeros --compara           # contra impressao_antes.txt
    py -3.12 -m scripts.design.impressao_numeros --fina --grava ARQ  # sem resumir listas (para achar a diferença)
    py -3.12 -m scripts.design.impressao_numeros --detalhe PREFIXO   # as folhas numéricas sob um caminho

O QUE ENTRA
- Páginas de partida, de jogadores e da prancheta: cada bloco JSON embutido (`<script
  type="application/json" id=...>` ou um literal JSON atribuído a um identificador, como
  `var DADOS = {...}` ou `radar: {...}`), nomeado pelo id/identificador. Cada número solto vira
  uma linha; uma lista só de números vira UMA linha com o hash dela (sha256 dos 16 primeiros
  hex, mais o tamanho) -- mudar um elemento muda o hash. Blocos com menos de TAMANHO_MINIMO
  caracteres são código (listas de constantes do JS), não dado, e ficam de fora.
- Landing (HTML estático, sem JSON): os números da linha do corpus, dos três números, e de
  cada card (placar e rounds). A FRASE do card ("... impôs 74 s de cegueira", depois "Decidida
  no round N") é o campo de texto que o design troca (entrega §10) e fica de fora.
- `numeros_citaveis.json`: todo valor numérico, um por linha, menos `testes.coletados` (a contagem de
  testes do repositório cresce a cada teste novo e não é dado das páginas).

O QUE NÃO ENTRA: texto. Campos novos de texto do design (nome dos lados na FACEIT, linha de
resumo dos grupos, `<title>`, descrição) não são números.

Se a comparação acusar diferença, é bug da fase: pare antes do merge.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
RAIZ = Path(__file__).resolve().parents[2]
DOCS = RAIZ / "docs"
NUMEROS = RAIZ / "data" / "processed" / "numeros_citaveis.json"
ANTES = RAIZ / "notas" / "design" / "impressao_antes.txt"
# a impressão fina do main (local, fora do git: 15 MB) para diagnosticar uma diferença
FINA = RAIZ / "data" / "interim" / "design_impressao_antes_fina.txt"

# Um literal JSON menor que isto, atribuído a um identificador, é constante de código (por
# exemplo `VELOCIDADES = [0.25, 0.5, 1, 2, 4]`), não dado embutido. Medido nas páginas de
# docs/: os blocos de dado têm de 1 KB para cima; as constantes do JS ficam abaixo de 120.
TAMANHO_MINIMO = 120

# Lista de objetos (ou de listas) com mais itens que isto vira UMA linha com o hash da projeção
# numérica de todos eles: sem isso a impressão passa de 15 MB (199 mil linhas, quase tudo a
# biblioteca de arremessos repetida nas 10 pranchetas). Detalhe de uma diferença: `--fina`.
LIMITE_DE_ITENS = 12

_ATRIBUICAO = re.compile(r"([A-Za-z_$][\w$]*)\s*[:=]\s*(?=[\[{])")
_SCRIPT_JSON = re.compile(r'<script[^>]*type="application/json"[^>]*id="([^"]+)"[^>]*>', re.I)
_NUMERO_NO_TEXTO = re.compile(r"\d+(?:[.,]\d+)*")


def _eh_numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _hash(lista: list) -> str:
    """Hash da projeção numérica de uma lista de escalares (o que não é número vira null)."""
    proj = [v if _eh_numero(v) else None for v in lista]
    bruto = json.dumps(proj, separators=(",", ":"), ensure_ascii=False)
    return f"lista n={len(lista)} sha256:{hashlib.sha256(bruto.encode('utf-8')).hexdigest()[:16]}"


def _projecao(obj):
    """A mesma estrutura, só com os números (o resto vira null), para o hash de um subárvore."""
    if isinstance(obj, dict):
        return {k: _projecao(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [_projecao(v) for v in obj]
    return obj if _eh_numero(obj) else None


def _tem_numero(obj) -> bool:
    if isinstance(obj, dict):
        return any(_tem_numero(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_tem_numero(v) for v in obj)
    return _eh_numero(obj)


def achata(obj, caminho: str, saida: dict[str, str], fina: bool = False) -> None:
    """Preenche `saida` com caminho -> valor, só do que é número. `fina` desliga o resumo
    das listas longas de objetos."""
    if isinstance(obj, dict):
        for k in sorted(obj):
            achata(obj[k], f"{caminho}.{k}" if caminho else str(k), saida, fina)
    elif isinstance(obj, list):
        if any(isinstance(v, (dict, list)) for v in obj):
            if not fina and len(obj) > LIMITE_DE_ITENS:
                if _tem_numero(obj):
                    bruto = json.dumps(_projecao(obj), separators=(",", ":"), ensure_ascii=False)
                    saida[caminho] = f"itens n={len(obj)} sha256:{hashlib.sha256(bruto.encode('utf-8')).hexdigest()[:16]}"
                return
            for i, v in enumerate(obj):
                achata(v, f"{caminho}[{i}]", saida, fina)
        elif any(_eh_numero(v) for v in obj):
            saida[caminho] = _hash(obj)
    elif _eh_numero(obj):
        saida[caminho] = repr(obj)


def blobs_da_pagina(texto: str) -> list[tuple[str, object]]:
    """Os literais JSON embutidos numa página: (nome, objeto), na ordem em que aparecem."""
    achados: list[tuple[str, object]] = []
    dec = json.JSONDecoder()
    # 1) <script type="application/json" id="x">{...}</script>
    for m in _SCRIPT_JSON.finditer(texto):
        fim_tag = texto.find("</script>", m.end())
        try:
            achados.append((m.group(1), json.loads(texto[m.end():fim_tag])))
        except ValueError:
            pass
    # 2) literais JSON atribuídos a um identificador dentro de qualquer <script> sem tipo
    for m in re.finditer(r"<script(?![^>]*type=\"application/json\")[^>]*>(.*?)</script>", texto, re.S):
        js = m.group(1)
        pos = 0
        for a in _ATRIBUICAO.finditer(js):
            if a.start() < pos:
                continue
            try:
                obj, fim = dec.raw_decode(js, a.end())
            except ValueError:
                continue
            if fim - a.end() >= TAMANHO_MINIMO:
                achados.append((a.group(1), obj))
                pos = fim
    return achados


def _tokens(fragmento: str) -> list[str]:
    sem_tags = re.sub(r"<[^>]+>", " ", fragmento)
    return sorted(_NUMERO_NO_TEXTO.findall(sem_tags))


def impressao_da_landing(texto: str, saida: dict[str, str]) -> None:
    """Números do HTML estático da landing (ver a docstring do módulo)."""
    m = re.search(r'id="corpus"[^>]*>(.*?)</p>', texto, re.S)
    if m:
        saida["index.html::corpus"] = " ".join(_tokens(m.group(1)))
    m = re.search(r'<section class="nums"[^>]*>(.*?)</section>', texto, re.S)
    if m:
        saida["index.html::tres_numeros"] = " ".join(_tokens(m.group(1)))
    cards = []
    for c in re.finditer(r'<a class="mcard"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', texto, re.S):
        href, corpo = c.group(1), c.group(2)
        placar = re.search(r'class="mscore">(.*?)</span>', corpo, re.S)
        rounds = re.search(r'class="mfoot"><span>(.*?)</span>', corpo, re.S)
        cards.append((href, " ".join(_tokens(placar.group(1))) if placar else "",
                      " ".join(_tokens(rounds.group(1))) if rounds else ""))
    for href, placar, rounds in sorted(cards):
        saida[f"index.html::card[{href}]"] = f"placar {placar} | rounds {rounds}"


def impressao(docs: Path = DOCS, fina: bool = False) -> dict[str, str]:
    saida: dict[str, str] = {}
    for f in sorted(docs.glob("*.html")):
        texto = f.read_text(encoding="utf-8")
        if f.name == "index.html":
            impressao_da_landing(texto, saida)
            continue
        vistos: dict[str, int] = {}
        for nome, obj in blobs_da_pagina(texto):
            vistos[nome] = vistos.get(nome, 0) + 1
            rotulo = nome if vistos[nome] == 1 else f"{nome}#{vistos[nome]}"
            achata(obj, f"{f.name}::{rotulo}", saida, fina)
    if NUMEROS.exists():
        achata(json.loads(NUMEROS.read_text(encoding="utf-8")), "numeros_citaveis.json", saida, fina)
    # A contagem de testes do repositório não é dado das páginas: cresce a cada teste novo.
    saida.pop("numeros_citaveis.json.testes.coletados", None)
    return saida


def para_texto(imp: dict[str, str]) -> str:
    return "".join(f"{k} = {v}\n" for k, v in sorted(imp.items()))


def le(arq: Path) -> dict[str, str]:
    out = {}
    for linha in arq.read_text(encoding="utf-8").splitlines():
        k, _, v = linha.partition(" = ")
        out[k] = v
    return out


def compara(antes: dict[str, str], depois: dict[str, str]) -> list[str]:
    """As diferenças: 'mudou', 'sumiu' ou 'apareceu', um caminho por linha."""
    dif = []
    for k in sorted(set(antes) | set(depois)):
        if k not in depois:
            dif.append(f"sumiu     {k} = {antes[k]}")
        elif k not in antes:
            dif.append(f"apareceu  {k} = {depois[k]}")
        elif antes[k] != depois[k]:
            dif.append(f"mudou     {k}: {antes[k]}  ->  {depois[k]}")
    return dif


def detalhe(prefixo: str) -> list[str]:
    """As folhas numéricas (sem hash) sob um caminho, nas páginas atuais."""
    pagina, _, resto = prefixo.partition("::")
    texto = (DOCS / pagina).read_text(encoding="utf-8")
    saida = []
    for nome, obj in blobs_da_pagina(texto):
        if resto and not (resto == nome or resto.startswith(nome + ".") or resto.startswith(nome + "[")):
            continue
        def folhas(o, c):
            if isinstance(o, dict):
                for k in sorted(o):
                    folhas(o[k], f"{c}.{k}")
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    folhas(v, f"{c}[{i}]")
            elif _eh_numero(o):
                saida.append(f"{c} = {o!r}")
        folhas(obj, f"{pagina}::{nome}")
    return [s for s in saida if s.startswith(prefixo)]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--detalhe" in argv:
        for linha in detalhe(argv[argv.index("--detalhe") + 1]):
            print(linha)
        return 0
    imp = impressao(fina="--fina" in argv)
    if "--grava" in argv:
        arq = Path(argv[argv.index("--grava") + 1])
        arq.write_text(para_texto(imp), encoding="utf-8", newline="\n")
        print(f"{len(imp)} linhas em {arq}")
        return 0
    if "--compara" in argv:
        i = argv.index("--compara")
        base = Path(argv[i + 1]) if i + 1 < len(argv) and not argv[i + 1].startswith("--") else (FINA if "--fina" in argv else ANTES)
        dif = compara(le(base), imp)
        print(f"{len(imp)} linhas contra {len(le(base))} em {base.name}: "
              f"{'nenhuma diferença numérica' if not dif else str(len(dif)) + ' diferença(s)'}")
        for d in dif[:200]:
            print("  " + d)
        return 1 if dif else 0
    sys.stdout.write(para_texto(imp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
