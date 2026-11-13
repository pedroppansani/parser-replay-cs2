"""CR1a: prova de que o plano dos comandos, depois de sair da prancheta para `comandos/plano.js`, faz EXATAMENTE o que fazia.

    py -3.12 -m scripts.design.prova_plano_dos_comandos grava ARQUIVO.json     # roda a bateria no código desta pasta
    py -3.12 -m scripts.design.prova_plano_dos_comandos compara A.json B.json  # compara duas gravações (antes e depois)

A bateria roda no navegador, em páginas geradas sozinhas (`build_html`), com as 10 fichas no mapa, em 4 mapas (Mirage, Dust2, Nuke com o andar de baixo e
Inferno) e 3 arrumações de fichas por mapa (duas ao acaso e uma perto das saídas reais da biblioteca):
  1. cerca de 120 frases por arrumação, de uma gramática com sorteio fixo (semente): mover, segurar, esperar, lançar as quatro granadas, "e depois", "ao mesmo
     tempo", horários do relógio e "do início", dois jogadores na mesma frase e comandos que se cortam. Para cada uma: o plano inteiro (`cmdPlano`: operações,
     chegadas, perguntas, avisos, cortes) e a linha de cada comando no cartão (`cmdLinha`), com as respostas que a tela dá às perguntas (levar a peça, chegar tarde, outra saída, sem arremesso real, a chegada na troca de andar). Só os ids (UUID novo a cada carga de página) viram marcadores posicionais e os carimbos de hora das operações viram `<hora>`.
  2. a busca da granada real (`cmdBuscaReal`): as 4 granadas x os 2 lados x os alvos do mapa x 3 posições da ficha.
  3. o caminho da tela: escrever, entender e aplicar 12 frases, comparando o texto do cartão e as operações gravadas na tática.
Cada resultado vira um hash; `compara` diz quantos batem e mostra a primeira diferença, se houver.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

MAPAS = ["de_mirage", "de_dust2", "de_nuke", "de_inferno"]
GRANADAS = ["smoke", "flash", "molotov", "he"]
HORARIOS = ["1:50", "1:40", "1:30", "1:20", "1:10", "1:00", "0:50", "0:40", "0:30"]
POR_ARRUMACAO = 120


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


_UUID = re.compile(r"^[0-9a-f]{32}$")
_CARIMBO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def _sem_ids(x, mapa: dict | None = None):
    """Os ids da prancheta (granada, passo...) são UUIDs novos a cada carga de página: viram marcadores POSICIONAIS (o mesmo id vira o mesmo marcador no resultado
    inteiro), então a estrutura e as igualdades entre ids continuam sendo comparadas; só o valor aleatório sai."""
    mapa = {} if mapa is None else mapa
    if isinstance(x, dict):
        return {k: _sem_ids(v, mapa) for k, v in x.items()}
    if isinstance(x, list):
        return [_sem_ids(v, mapa) for v in x]
    if isinstance(x, str) and _UUID.match(x):
        return mapa.setdefault(x, f"<id{len(mapa)}>")
    if isinstance(x, str) and _CARIMBO.match(x):      # o carimbo de hora de cada operação (`em`) é a hora da rodada
        return "<hora>"
    return x


def _nomes(ctx: dict) -> list[str]:
    nomes = [p["nome"] for p in ctx["pontos"] if p["tipo"] != "bombsite"]
    nomes += [a["texto"] for a in ctx["areas"]]
    return sorted(set(nomes))


def _frases(rnd: random.Random, nomes: list[str], n: int) -> list[str]:
    jog = [f"{l} {i}" for l in ("tr", "ct") for i in range(1, 6)]

    def uma() -> str:
        j, lugar, h = rnd.choice(jog), rnd.choice(nomes), rnd.choice(HORARIOS)
        t = rnd.randrange(14)
        if t == 0:
            return f"{j} corre pro {lugar} aos {h}"
        if t == 1:
            return f"{j} anda ate {lugar} aos {h}"
        if t == 2:
            return f"{j} agacha em {lugar} aos {h}"
        if t == 3:
            return f"{j} segura {lugar} ate {rnd.choice(HORARIOS)}"
        if t == 4:
            return f"{j} espera {rnd.choice([3, 5, 8])} segundos aos {h}"
        if t == 5:
            return f"{j} joga {rnd.choice(GRANADAS)} no {lugar} aos {h}"
        if t == 6:
            return f"{j} corre pro {lugar} aos {h} e depois pro {rnd.choice(nomes)}"
        if t == 7:
            return f"{j} corre pro {lugar} aos {h} e depois joga {rnd.choice(GRANADAS)} no {rnd.choice(nomes)}"
        if t == 8:
            return f"{j} joga {rnd.choice(GRANADAS)} no {lugar} aos {h}, {rnd.choice(jog)} corre pro {rnd.choice(nomes)} ao mesmo tempo"
        if t == 9:
            return f"{j} e {rnd.choice(jog)} correm pro {lugar} aos {h}"
        if t == 10:
            return f"{j} corre pro {lugar} aos {h}, {j} corre pro {rnd.choice(nomes)} aos {rnd.choice(HORARIOS)}"       # os dois se cortam
        if t == 11:
            return f"{j} corre pro {lugar} aos {rnd.choice([20, 30, 45])} segundos do inicio"
        if t == 12:
            return f"{j} joga {rnd.choice(GRANADAS)} no {lugar} aos {h} e {rnd.choice(jog)} joga {rnd.choice(GRANADAS)} no {rnd.choice(nomes)} aos {rnd.choice(HORARIOS)}"
        return f"{j} corre pro {lugar} aos {h}, depois segura {rnd.choice(nomes)} ate {rnd.choice(HORARIOS)}"
    return [uma() for _ in range(n)]


AVALIA = """([f, c, variante]) => {
  const I = Prancheta._interno, L = LeitorDeComandos.le(f, c);
  if (L.perguntas.length || !L.acoes.length) return { pulou: true, perguntas: L.perguntas.map(p => p.codigo).sort() };
  // as respostas que a tela dá às perguntas do plano (decidir levar a peça, aceitar chegar tarde, outra saída, a chegada na troca de andar, sem arremesso real)
  L.acoes.forEach(a => {
    if (a.tipo === "lancar") {
      if (variante === 1 || variante === 2 || variante === 4) a.gr_decisao = "levar";
      if (variante === 2) a.gr_tarde_ok = true;
      if (variante === 3) a.gr_decisao = "sem";
      if (variante === 4) a.gr_i = 1;
    }
    if (variante === 5 && a.alvo && a.alvo.andar === "baixo") a.chegada_t = ((a.quando && a.quando.t_decorrido) || 40) + 6;
  });
  let plano;
  try { plano = I.cmdPlano(L); } catch (e) { return { erro: String(e && e.message || e) }; }
  const linhas = L.acoes.map(a => { try { return I.cmdLinha(a, plano); } catch (e) { return "ERRO " + String(e && e.message || e); } });
  return { plano: plano, linhas: linhas };
}"""

BUSCA = """([arma, alvo, lado, x, y]) => {
  const b = Prancheta._interno.cmdBuscaReal(arma, alvo, lado, { x: x, y: y });
  return { estado: b.estado, mesmo: b.mesmo, outro: b.outro, grupos: b.grupos.map(g => [g.r.id, Math.round(g.d * 100) / 100, Math.round(g.dist * 100) / 100, g.voo, g.jogadas]) };
}"""

PECA = """([x, y, nivel, lado, rotulo]) => { const I = Prancheta._interno, S = I.S;
  I.emiteLote([["cria_peca", { peca: "demo-" + lado + rotulo, lado: lado, rotulo: rotulo, passo: S.estado.passos[0].passo, x: x, y: y, nivel: nivel }]]); }"""


def _abre(nav, pagina: Path, aba: bool = True):
    pg = nav.new_page()
    pg.goto(pagina.as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    if aba:   # abrir a aba carrega o plano e os tempos reais de corrida (sem isso o corpus não entraria na conta)
        pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
    return pg


def _fichas(pg, rnd: random.Random, posicoes: list[dict], saidas: dict | None = None) -> None:
    for lado in ("t", "ct"):
        for rotulo in "12345":
            if saidas and saidas.get(lado):          # perto de uma saída real da biblioteca: a granada real entra na conta sem a pergunta "longe"
                o = rnd.choice(saidas[lado])
                pg.evaluate(PECA, [o[0], o[1], 0, lado, rotulo])
                continue
            p = rnd.choice(posicoes)
            pg.evaluate(PECA, [p["x"], p["y"], 1 if p.get("andar") == "baixo" else 0, lado, rotulo])


def _saidas(mapa: str) -> dict:
    caminho = RAIZ / "data" / "lineups" / f"{mapa}.json"
    if not caminho.exists():
        return {}
    por: dict = {"t": [], "ct": []}
    for r in json.loads(caminho.read_text(encoding="utf-8"))["arremessos"]:
        if r["lado"] in por and r.get("voo_s") is not None:
            por[r["lado"]].append(r["origem"])
    return {k: v[::max(1, len(v) // 400)] for k, v in por.items()}


def roda() -> dict:
    from playwright.sync_api import sync_playwright
    from scripts.build_tactics_page import build_html
    from scripts.comandos_contexto import contexto
    saida: dict = {"frases": {}, "buscas": {}, "tela": {}, "amostra": {}, "categorias": {}}

    def conta(r: dict) -> None:
        """Quanto a bateria exercita de cada ramo do plano (se só houvesse frases que pulam, a prova não provaria nada)."""
        if r.get("pulou"):
            tipos = ["pulou:" + ",".join(r["perguntas"])]
        elif "erro" in r:
            tipos = ["erro"]
        else:
            pl, tipos = r["plano"], ["plano"]
            tipos += [k for k in ("problemas", "avisos", "cortados", "granadas", "chegadas") if pl.get(k)]
            tipos += ["ops:" + o[0] for o in pl["ops"]]
            if pl.get("falta"):
                tipos.append("falta")
            if pl.get("pergunta"):
                tipos.append("pergunta:" + pl["pergunta"]["tipo"])
            if pl.get("espera"):
                tipos.append("espera")
            tipos += ["granada_real"] * any(g.get("r") for g in pl["granadas"].values()) + ["granada_sem"] * any(g.get("sem") for g in pl["granadas"].values())
            tipos += ["chegada_real"] * any(c.get("tipo") == "real" for c in pl["chegadas"].values()) + ["chegada_estimada"] * any(c.get("tipo") == "estimado" for c in pl["chegadas"].values())
        for t in set(tipos):
            saida["categorias"][t] = saida["categorias"].get(t, 0) + 1
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for mapa in MAPAS:
            ctx = contexto(mapa, so_conferidos=True)
            ctx["jogadores"] = [{"lado": l, "num": i} for l in ("tr", "ct") for i in range(1, 6)]
            nomes = _nomes(ctx)
            posicoes = [{"x": q["x"], "y": q["y"], "andar": q.get("andar")} for q in ctx["pontos"]] + [{"x": a["x"], "y": a["y"], "andar": a.get("andar")} for a in ctx["areas"]]
            if not nomes or not posicoes:
                saida["frases"][f"{mapa}|sem-contexto"] = "-"
                continue
            pagina = Path(tempfile.mkdtemp(prefix="prova_plano_")) / f"{mapa}.html"
            pagina.write_text(build_html(mapa), encoding="utf-8")
            saidas = _saidas(mapa)
            for arrumacao in (0, 1, 2):
                rnd = random.Random(f"{mapa}:{arrumacao}")
                pg = _abre(nav, pagina)
                _fichas(pg, rnd, posicoes, saidas if arrumacao == 2 else None)
                for i, frase in enumerate(_frases(rnd, nomes, POR_ARRUMACAO)):
                    tem_granada = " joga " in frase
                    for variante in (range(5) if tem_granada else (0, 5)):
                        r = _sem_ids(pg.evaluate(AVALIA, [frase, ctx, variante]))
                        conta(r)
                        chave = f"{mapa}|{arrumacao}|{i}|v{variante}|{frase}"
                        saida["frases"][chave] = _hash(r)
                        if len(saida["amostra"]) < 12 and "plano" in r and r["plano"]["ops"]:
                            saida["amostra"][chave] = r
                # a busca da granada real: 4 granadas x 2 lados x os alvos x 3 posições
                alvos = [q for q in ctx["pontos"] if q["tipo"] != "bombsite"][:8]
                for arma in GRANADAS:
                    for lado in ("t", "ct"):
                        for q in alvos:
                            alvo = {"tipo": "ponto", "id": q["id"], "ids": [q["id"]], "nome": q["nome"], "x": q["x"], "y": q["y"], "andar": q.get("andar", "único")}
                            for k in range(3):
                                o = rnd.choice(posicoes)
                                saida["buscas"][f"{mapa}|{arrumacao}|{arma}|{lado}|{q['nome']}|{k}"] = _hash(pg.evaluate(BUSCA, [arma, alvo, lado, o["x"], o["y"]]))
                pg.close()
            # o caminho da tela: escrever, entender e aplicar
            rnd = random.Random(f"{mapa}:tela")
            for i, frase in enumerate(_frases(rnd, nomes, 12)):
                pg = _abre(nav, pagina)
                _fichas(pg, random.Random(f"{mapa}:tela:fichas"), posicoes, saidas)
                pg.fill("#pr-cmd-texto", frase)
                pg.click("#pr-cmd-entender")
                texto = pg.inner_text("#pr-cmd-resultado")
                aplicou = pg.is_enabled("#pr-cmd-aplicar")
                if aplicou:
                    pg.click("#pr-cmd-aplicar")
                ops = _sem_ids(pg.evaluate("() => JSON.parse(JSON.stringify(Prancheta._interno.S.doc.operacoes))"))
                saida["tela"][f"{mapa}|{i}|{frase}"] = _hash({"texto": texto, "aplicou": aplicou, "ops": ops})
                pg.close()
        nav.close()
    resumo = {k: len(v) for k, v in saida.items()}
    saida["resumo"] = resumo
    saida["geral"] = _hash({k: saida[k] for k in ("frases", "buscas", "tela", "categorias")})
    return saida


def compara(a: dict, b: dict) -> int:
    ruim = 0 if a["categorias"] == b["categorias"] else 1
    print("categorias iguais:", a["categorias"] == b["categorias"])
    for bloco in ("frases", "buscas", "tela"):
        ka, kb = a[bloco], b[bloco]
        so_a, so_b = sorted(set(ka) - set(kb)), sorted(set(kb) - set(ka))
        dif = [k for k in sorted(set(ka) & set(kb)) if ka[k] != kb[k]]
        print(f"{bloco}: {len(ka)} contra {len(kb)}; iguais {len(ka) - len(dif) - len(so_a)}; diferentes {len(dif)}; só no primeiro {len(so_a)}; só no segundo {len(so_b)}")
        for k in dif[:3] + so_a[:2] + so_b[:2]:
            print("   ", k[:160])
        ruim += len(dif) + len(so_a) + len(so_b)
    print("hash geral:", a["geral"], b["geral"], "IGUAIS" if a["geral"] == b["geral"] and not ruim else "DIFERENTES")
    return 0 if a["geral"] == b["geral"] and not ruim else 1


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "grava":
        r = roda()
        Path(sys.argv[2]).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print("gravado:", sys.argv[2], r["resumo"], "geral", r["geral"])
        return 0
    if len(sys.argv) == 4 and sys.argv[1] == "compara":
        return compara(*(json.loads(Path(x).read_text(encoding="utf-8")) for x in sys.argv[2:4]))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
