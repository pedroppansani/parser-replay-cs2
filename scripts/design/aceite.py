"""
Critérios de aceite (entrega-sala-de-demo §15) medidos com Playwright contra `docs/`, o
site gerado por `py -3.12 -m scripts.build_site` (adaptado do roteiro do protótipo).

    py -3.12 -m scripts.design.aceite             # imprime o relatório e devolve 1 se algo falhar
    py -3.12 -m scripts.design.aceite --todas     # A7 em todas as partidas e abas (mais lento)
    py -3.12 -m scripts.design.aceite --so A2,A3,A4,A6   # só alguns critérios (cada fase responde por uns)

Os seletores que dependem da estrutura da página ficam em SEL, para acompanhar as fases.

Mede, em 375x667, 375x812 e 1440x900:
  1. rolagem horizontal da página (scrollWidth <= largura)
  2. controle de tocar do replay visível sem rolar (abrindo partida.html#replay
     e clicando na aba Replay a partir do Resumo)
  3. contraste de TODO texto visível contra o fundo efetivo (>= 4,5:1; >= 3:1
     para texto grande, >= 24 px ou >= 18,66 px em negrito)
  4. borda de controle (botão, chip, campo) contra o fundo (>= 3:1)
  5. alvo de toque >= 44x44 (links dentro de frase ficam de fora, regra WCAG 2.5.8)
  6. famílias de fonte carregadas (máximo 2) e mono só em número
  7. nenhum "Time A" / "Time B"
"""
import re
import sys
sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

from scripts.design._comum import DOCS, chrome, url_de

# Seletores da estrutura real (docs/). Mudam com as fases B1 e B2: ajustar aqui.
SEL = {
    "tocar": "#play",                    # controle de tocar do replay
    "aba_replay": '[data-tab="replay"]',
}
PARTIDA = "match_02.html"                # Mirage, profissional: o exemplo das medições
ABAS = ["replay", "insights", "rounds", "jogadores", "perfil", "estilos"]   # data-tab de cada aba
# cada item é (página, aba ou None)
PAGINAS = [("index.html", None)] + [(PARTIDA, a) for a in ABAS] + [
    ("prancheta_de_mirage.html", None), ("prancheta_de_nuke.html", None), ("jogadores.html", None)]
TELAS = [(375, 667), (375, 812), (1440, 900)]
LISTA = 8   # quantos itens de cada falha entram no relatório

JS = r"""
() => {
  function rgba(s){ const m=s.match(/rgba?\(([^)]+)\)/); if(!m) return null; const p=m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0],p[1],p[2],p.length>3?p[3]:1]; }
  function lum(c){ const f=v=>{v/=255;return v<=0.04045?v/12.92:Math.pow((v+0.055)/1.055,2.4)}; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); }
  function ratio(a,b){ const la=lum(a), lb=lum(b); return (Math.max(la,lb)+0.05)/(Math.min(la,lb)+0.05); }
  function mistura(fr,bk){ const a=fr[3]; return [fr[0]*a+bk[0]*(1-a), fr[1]*a+bk[1]*(1-a), fr[2]*a+bk[2]*(1-a), 1]; }
  function fundo(el){ // pilha de fundos até achar um opaco; imagens e gradientes contam como "desconhecido"
    const camadas=[]; let e=el;
    while(e && e.nodeType===1){ const s=getComputedStyle(e);
      if(s.backgroundImage && s.backgroundImage!=="none" && !/gradient/.test(s.backgroundImage)) return null;
      const c=rgba(s.backgroundColor); if(c && c[3]>0){ camadas.push(c); if(c[3]>=1) break; } e=e.parentElement; }
    let base=[11,15,20,1]; for(let i=camadas.length-1;i>=0;i--) base=mistura(camadas[i],base); return base; }
  function visivel(el){ const r=el.getBoundingClientRect(); const s=getComputedStyle(el); return r.width>0&&r.height>0&&s.visibility!=="hidden"&&s.display!=="none"&&parseFloat(s.opacity)>0; }
  function opacidadeAcumulada(el){ let o=1, e=el; while(e&&e.nodeType===1){ o*=parseFloat(getComputedStyle(e).opacity); e=e.parentElement; } return o; }
  const res={sw:document.documentElement.scrollWidth, vw:innerWidth, texto:[], textoMin:99, borda:[], toque:[], mono:[], timeAB:false, fontes:[]};
  // 3. contraste de texto
  const walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const vistos=new Set();
  while(walker.nextNode()){ const n=walker.currentNode; if(!n.nodeValue.trim()) continue; const el=n.parentElement; if(!el||vistos.has(el)) continue; vistos.add(el);
    if(el.closest("svg")||el.closest("[hidden]")||el.closest("details:not([open]) > :not(summary)")) continue;
    if(!visivel(el)) continue;
    if(el.closest("[disabled],[aria-disabled=true]")) continue;           // WCAG 1.4.3: controle desativado é exceção
    if(el.closest(".alterna-notas")) continue;
    const s=getComputedStyle(el); const c=rgba(s.color); const b=fundo(el); if(!c||!b) continue;
    const op=opacidadeAcumulada(el); const cf=mistura([c[0],c[1],c[2],c[3]*op], b);
    const r=ratio(cf,b); const px=parseFloat(s.fontSize), bold=parseInt(s.fontWeight)>=700;
    const lim=(px>=24||(px>=18.66&&bold))?3:4.5;
    if(r<res.textoMin) res.textoMin=r;
    if(r<lim) res.texto.push(el.tagName+"."+el.className+" '"+n.nodeValue.trim().slice(0,30)+"' "+r.toFixed(2)+" < "+lim);
  }
  // 4. borda de controle
  document.querySelectorAll("button:not([role=tab]):not(.play), .btn:not(.principal):not(.fantasma), .chip, select, input[type=text]").forEach(el=>{
    if(!visivel(el)||el.closest("[hidden]")) return; if(el.matches("[disabled],[aria-disabled=true]")) return;
    const s=getComputedStyle(el); const bc=rgba(s.borderTopColor); const b=fundo(el.parentElement); if(!bc||!b||parseFloat(s.borderTopWidth)===0) return;
    const r=ratio(mistura(bc,b),b); if(r<3) res.borda.push(el.className+" "+r.toFixed(2)); });
  // 5. toque
  document.querySelectorAll("a[href], button, select, input, summary, [role=tab], [role=slider]").forEach(el=>{
    if(!visivel(el)||el.closest("[hidden]")||el.closest("svg")) return;
    if(el.tagName==="A" && el.closest("p, li, figcaption, dd, td, .proto-nota") && !el.classList.contains("btn")) return;  // link dentro de frase: exceção
    if(el.closest(".abas-moldura") && el.classList.contains("abas-mais") && getComputedStyle(el).display==="none") return;
    const r=el.getBoundingClientRect(); if(r.width<43.5||r.height<43.5) res.toque.push((el.tagName+"."+el.className+" '"+(el.textContent||el.getAttribute("aria-label")||"").trim().slice(0,18)+"' ").slice(0,70)+Math.round(r.width)+"x"+Math.round(r.height)); });
  // 6. mono só em número
  document.querySelectorAll("body *").forEach(el=>{ if(!visivel(el)||el.closest("svg")) return; const s=getComputedStyle(el);
    if(!/JetBrains/.test(s.fontFamily.split(",")[0])) return;
    const proprio=[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.nodeValue).join(" ");
    const palavras=(proprio.replace(/\{[a-z_]+\}/g,"").match(/[A-Za-zÀ-ú]{3,}/g)||[]); /* {erro_rating} é marcador de número */ if(palavras.length) res.mono.push(el.tagName+"."+el.className+" '"+proprio.trim().slice(0,30)+"'"); });
  res.timeAB=/\bTime [AB]\b/.test(document.body.innerText);
  // fallbacks "… Fallback" são apelidos de fontes do sistema (local()), sem download: não contam como família carregada
  document.fonts.forEach(f=>{ const n=f.family.replace(/"/g,""); if(f.status==="loaded" && !/Fallback$/.test(n)) res.fontes.push(n); });
  res.fontes=[...new Set(res.fontes)];
  return res;
}
"""

def tocar_visivel(pg):
    return pg.evaluate("""()=>{const t=document.querySelector('#play'); if(!t) return null; const b=t.getBoundingClientRect();
      const el=document.elementFromPoint(b.left+b.width/2, b.top+b.height/2);
      return {topo:Math.round(b.top), base:Math.round(b.bottom), altura:innerHeight, rolagem:scrollY, visivel:(el===t||t.contains(el)) && b.bottom<=innerHeight && b.top>=0};}""")

def a7_todas(b):
    """A7 (entrega §10): nenhuma partida com "Time A" / "Time B", em todas as abas."""
    ruins = []
    arqs = sorted(DOCS.glob("match_*.html"))
    for f in arqs:
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(f.as_uri()); pg.wait_for_timeout(300)
        for aba in ABAS:
            pg.click(f'[data-tab="{aba}"]')
            if re.search(r"\bTime [AB]\b", pg.evaluate("document.body.innerText")):
                ruins.append(f"{f.name}::{aba}")
        pg.close()
    print(f"== A7: 'Time A/B' em {len(arqs)} partidas x {len(ABAS)} abas: "
          f"{'nenhuma ocorrência  PASSA' if not ruins else 'FALHA em ' + ', '.join(ruins[:8])}")
    return len(ruins)


def criterios() -> set[str]:
    """Os critérios a medir: todos, ou os de `--so A2,A3,...`."""
    if "--so" in sys.argv:
        return {x.strip().upper() for x in sys.argv[sys.argv.index("--so") + 1].split(",")}
    return {"A1", "A2", "A3", "A4", "A5", "A6", "A7"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    todas = "--todas" in sys.argv
    quais = criterios()
    falhas = 0
    p = sync_playwright().start(); b = chrome(p)
    print("== A1: controle de tocar visível sem rolar ==")
    for w, h in TELAS if "A1" in quais else ():
        for modo in ("abre #replay", "clica na aba Replay"):
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.goto(url_de(PARTIDA + ("#replay" if modo == "abre #replay" else ""))); pg.wait_for_timeout(900)
            if modo != "abre #replay":
                pg.click(SEL["aba_replay"]); pg.wait_for_timeout(300)
            r = tocar_visivel(pg); ok = bool(r and r["visivel"] and r["rolagem"] == 0)
            falhas += not ok
            print(f"{w}x{h} {modo:<20} topo {r['topo']} base {r['base']} (tela {r['altura']}, rolagem {r['rolagem']})  {'PASSA' if ok else 'FALHA'}")
            pg.close()
    print()
    for w, h in TELAS:
        print(f"== {w}x{h} ==")
        for pagina, aba in PAGINAS:
            pag = pagina + (f"::{aba}" if aba else "")
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.goto(url_de(pagina)); pg.wait_for_timeout(1100)
            if aba:
                pg.click(f'[data-tab="{aba}"]'); pg.wait_for_timeout(400)
            for d in pg.query_selector_all("details"): d.evaluate("d=>d.open=true")
            r = pg.evaluate(JS)
            erros = []
            if "A2" in quais and r["sw"] > r["vw"]: erros.append(f"A2 rolagem horizontal {r['sw']}>{r['vw']}")
            if "A3" in quais and r["texto"]: erros.append(f"A3 {len(r['texto'])} textos abaixo do limiar: " + "; ".join(r["texto"][:LISTA]))
            if "A4" in quais and r["borda"]: erros.append("A4 borda < 3:1: " + "; ".join(r["borda"][:LISTA]))
            if "A5" in quais and r["toque"]: erros.append(f"A5 {len(r['toque'])} alvos < 44px: " + "; ".join(r["toque"][:LISTA]))
            if "A6" in quais and r["mono"]: erros.append(f"A6 {len(r['mono'])} mono com palavra: " + "; ".join(r["mono"][:LISTA]))
            if "A7" in quais and r["timeAB"]: erros.append('A7 "Time A/B" na página')
            fam = [f for f in r["fontes"]]
            if "A6" in quais and len(fam) > 2: erros.append("A6 famílias: " + ", ".join(fam))
            falhas += bool(erros)
            print(f"{pag:<34} largura {r['sw']:>4}  texto min {r['textoMin']:5.2f}:1  fontes {'+'.join(fam) or '-'}  {'PASSA' if not erros else 'FALHA'}")
            for e in erros: print("    - " + e)
            pg.close()
        print()
    if todas:
        falhas += bool(a7_todas(b))
    b.close(); p.stop()
    print("RESULTADO:", "PASSA" if falhas == 0 else f"FALHA ({falhas})")
    return 1 if falhas else 0

if __name__ == "__main__":
    raise SystemExit(main())
