"""CR1c: prova de que o leitor de comandos (`comandos/leitor.js`) lê EXATAMENTE como lia quando o contexto não traz nicks (o caso da prancheta).

    py -3.12 -m scripts.design.prova_leitor_dos_comandos grava ARQUIVO.json     # roda a bateria no código desta pasta
    py -3.12 -m scripts.design.prova_leitor_dos_comandos compara A.json B.json  # compara duas gravações (antes e depois)

Roda no `node` (o leitor é puro). Para cada mapa (Mirage, Dust2, Nuke, Inferno), com o contexto da prancheta (`contexto(mapa, so_conferidos=True)`, jogadores TR 1..5 e CT 1..5):
  1. cerca de 360 frases da gramática da prova do plano (mover, segurar, esperar, granadas, "e depois", "ao mesmo tempo", horários, dois jogadores, comandos que se cortam)
     e mais frases escritas à mão com as formas que mais variam ("o 4", "jogador 2", "ct 3", "tr 1 e tr 2", "ele", funções, números por extenso, "do início", horários que não existem);
  2. a leitura inteira (`le`): ações, perguntas, avisos, trechos entendidos e não entendidos, com o JSON canônico (chaves em ordem) virando um hash;
  3. cada pergunta respondida (`responde`) com cada uma das suas opções (até 3), e o hash da leitura resultante; e `horario` em 12 textos.
`compara` diz quantos hashes batem e mostra os primeiros que diferem.
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

MAPAS = ["de_mirage", "de_dust2", "de_nuke", "de_inferno"]
A_MAO = [
    "o 4 joga smoke no janelão aos 1:05", "o 2 corre pro meio aos 1:30", "jogador 3 anda ate a b aos 0:50", "ct 3 segura meio ate 0:45", "tr 1 e tr 2 correm pro meio aos 1:10",
    "tr 2 corre pra b aos 1:20 e depois ele segura a tv", "o awper joga flash no meio aos 1:00", "o entry fragger corre pra a aos 1:40", "tr um corre pro meio aos 1:10",
    "ct dois joga molotov na caverna aos 1:15", "tr 3 espera 5 segundos aos 1:20", "tr 3 corre pro meio aos 40 segundos do inicio", "tr 3 corre pro meio aos 40 segundos",
    "tr 4 corre pro meio aos 9:99", "tr 5 roda pra B aos 0:30", "ninguem corre pro meio", "corre pro meio aos 1:10", "tr 2 vai pro B e depois pro meio",
    "tr 2 corre pro meio aos 1:30, depois segura b ate 0:50", "tr 1 joga smoke no meio e ct 1 joga flash no meio aos 1:10", "o 5 joga he na tv aos 0:40",
    "ct 2 ao mesmo tempo tr 2 corre pro meio aos 1:10", "tr 1 corre pro lugar que nao existe aos 1:10", "o 4", "tr 2", "joga smoke", "aos 1:10",
]
HORARIOS = ["1:20", "aos 1:20", "40 s do inicio", "40 segundos", "0:30", "2:30", "10", "1:05 e meio", "depois", "", "agora", "aos 0:07"]

NODE = r"""
const fs = require("fs"), crypto = require("crypto");
const L = require(process.argv[2]);
const dados = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const canon = x => Array.isArray(x) ? x.map(canon) : x && typeof x === "object" ? Object.fromEntries(Object.keys(x).sort().map(k => [k, canon(x[k])])) : x;
const h = x => crypto.createHash("sha256").update(JSON.stringify(canon(x)) ).digest("hex").slice(0, 16);
const clona = x => JSON.parse(JSON.stringify(x));
const out = { leituras: {}, respostas: {}, horarios: {} };
for (const mapa of Object.keys(dados.contextos)) {
  const ctx = dados.contextos[mapa];
  dados.frases[mapa].forEach((f, i) => {
    const chave = mapa + "|" + i + "|" + f;
    let r;
    try { r = L.le(f, ctx); } catch (e) { out.leituras[chave] = "ERRO " + String(e.message || e); return; }
    out.leituras[chave] = h(r);
    r.perguntas.forEach((p, ip) => (p.opcoes || []).slice(0, 3).forEach((o, io) => {
      const c = chave + "|p" + ip + "o" + io;
      try { const r2 = L.responde(clona(r), ip, o.valor, ctx); out.respostas[c] = h(r2); } catch (e) { out.respostas[c] = "ERRO " + String(e.message || e); }
    }));
  });
  dados.horarios.forEach(t => { try { out.horarios[mapa + "|" + t] = h(L.horario(t, ctx)); } catch (e) { out.horarios[mapa + "|" + t] = "ERRO " + String(e.message || e); } });
}
process.stdout.write(JSON.stringify(out));
"""


def _dados() -> dict:
    from scripts.comandos_contexto import contexto
    from scripts.design.prova_plano_dos_comandos import _frases, _nomes
    contextos, frases = {}, {}
    for mapa in MAPAS:
        ctx = contexto(mapa, so_conferidos=True)
        ctx["jogadores"] = [{"lado": l, "num": i} for l in ("tr", "ct") for i in range(1, 6)]
        contextos[mapa] = ctx
        nomes = _nomes(ctx) or ["meio"]
        frases[mapa] = A_MAO + _frases(random.Random(f"leitor:{mapa}"), nomes, 360)
    return {"contextos": contextos, "frases": frases, "horarios": HORARIOS}


def roda() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="prova_leitor_"))
    (tmp / "run.js").write_text(NODE, encoding="utf-8")
    (tmp / "dados.json").write_text(json.dumps(_dados(), ensure_ascii=False), encoding="utf-8")
    leitor = (RAIZ / "dashboard" / "web" / "comandos" / "leitor.js").as_posix()
    r = subprocess.run(["node", str(tmp / "run.js"), leitor, str(tmp / "dados.json")], capture_output=True, text=True, encoding="utf-8", timeout=600)
    if r.returncode:
        raise SystemExit(r.stderr[-1500:])
    out = json.loads(r.stdout)
    out["resumo"] = {k: len(v) for k, v in out.items()}
    out["geral"] = hashlib.sha256(json.dumps({k: out[k] for k in ("leituras", "respostas", "horarios")}, sort_keys=True).encode()).hexdigest()[:16]
    return out


def compara(a: dict, b: dict) -> int:
    ruim = 0
    for bloco in ("leituras", "respostas", "horarios"):
        ka, kb = a[bloco], b[bloco]
        so_a, so_b = sorted(set(ka) - set(kb)), sorted(set(kb) - set(ka))
        dif = [k for k in sorted(set(ka) & set(kb)) if ka[k] != kb[k]]
        print(f"{bloco}: {len(ka)} contra {len(kb)}; iguais {len(ka) - len(dif) - len(so_a)}; diferentes {len(dif)}; só no primeiro {len(so_a)}; só no segundo {len(so_b)}")
        for k in dif[:3] + so_a[:2] + so_b[:2]:
            print("   ", k[:170])
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
