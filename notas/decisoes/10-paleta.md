# Decisão 10: Paleta do dashboard foi validada para daltonismo e contraste

- **ID:** 10
- **Status:** vigente
- **Data:** 2026-09-20
- **Resumo:** Paleta validada para daltonismo e contraste (tema escuro, decisão 44); cor só com `metrics.paleta`.

## Texto

10. **Paleta do dashboard foi validada para daltonismo e contraste.** O scatter
    de clusters é facetado (um painel por cluster) porque nenhuma quarta cor
    passa nos critérios junto das três primeiras no modo escuro. Não troque por
    4 cores num gráfico só.

    Nos gráficos da partida (vantagem e probabilidade de vitória), por pedido
    do Pedro: Time A azul `#2a78d6`, Time B laranja `#eb6834`, round decisivo
    **verde esmeralda escuro `#0b6b4a`** (2026-09-20, no lugar do roxo
    `#4a3aa7`). A linha da diferença de rounds é uma medida só e fica em tinta
    neutra; a cor de cada time está nas áreas e nas bolinhas, e empate é cinza.

    A TROCA CORRIGIU UM DIAGNÓSTICO MEU, e o registro antigo estava errado: ele
    dizia que "esmeralda passava por menos (ΔE 9,2) e com contraste 2,8:1",
    como se a cor tivesse sido reprovada. O que foi reprovado era o esmeralda
    CLARO (`#1baf7a`, o `--aqua` do tema) -- e o defeito era a LUMINÂNCIA, não
    o matiz. Medido de novo com `metrics/paleta.py` (ΔE2000 e dicromacia
    por Viénot 1999), o esmeralda escuro empata com o roxo no critério mais
    duro: pior par para daltônico ΔE **14,5** contra 14,9 do roxo (alvo 8),
    visão normal 40,6 contra 23,1, contraste no branco 6,53:1 contra 8,56:1.
    O piso é esse: `#0f8f63` já cai para ΔE 9,0 e `#1baf7a` reprova no
    contraste. **Não clareie o verde sem rodar o script.**

## Revisão: tema escuro (decisão 44)

**Revisão de 2026-10-04 — tema escuro e contraste medido contra o fundo do tema.**

**O que mudou.** O site passou a ter um tema único, escuro (direção "Sala de demo", escolha do Pedro). O critério de contraste do `metrics/paleta.py` deixa de ser "contraste no branco ≥ 3:1" e passa a ser contraste contra os fundos do tema onde cada cor aparece: página `#0b0f14`, superfície `#121820`, superfície elevada `#1a222d`, radar `#0f141b` e linha do tempo `#0e131a`. Cor de texto precisa de 4,5:1; cor de marca (peça, ícone, barra, borda de controle, foco) precisa de 3:1. O critério de daltonismo não muda: ΔE2000 ≥ 8 no pior par, protanopia e deuteranopia (Viénot 1999), agora por grupo de cores que aparecem juntas.

**Por quê.** Medir contra o branco só fazia sentido com página branca. No tema escuro o mesmo critério reprovaria o TR dourado (2,23:1 no branco, 8,60:1 no fundo real) e aprovaria cores que somem no fundo escuro. Smoke e flash, que sempre foram desenhadas sobre o radar escuro, eram "falha esperada" no critério antigo; agora são medidas onde aparecem.

**Cada cor tem um papel.** Molotov deixou de ser o laranja do TR (antes os dois eram `#eb6834`, ΔE 0). Destaque e round decisivo usam só o verde do decisivo, nunca a cor de um lado. Vitória, link e neutro não têm matiz próprio: vêm com palavra, sublinhado ou tracejado.

| Cor | Antes (critério: branco) | Depois (critério: fundo do tema) |
|---|---|---|
| CT | `#2a78d6` — 4,42:1 no branco | `#4a90e8` marca 5,48–5,90:1; `#6ea8f2` texto 6,52–7,82:1 |
| TR | `#eb6834` — 3,20:1 no branco | `#e0a23a` marca 7,98–8,60:1; `#e9b65a` texto 8,62–10,34:1 |
| Decisivo | `#0b6b4a` — 6,53:1 no branco | `#2fae7c` texto 5,70–6,83:1 |
| Smoke | `#9fb0c2` — "falha esperada" (2,22:1 no branco) | `#d1d9e0` 12,95:1 no radar |
| Flash | `#e8b53a` — "falha esperada" (1,89:1) | `#f9f5b8` 16,53:1 no radar |
| HE | `#d1495b` | `#ff4da6` 6,04:1 no radar |
| Molotov | `#eb6834` (= TR, ΔE 0) | `#d65d00` 4,77:1 no radar; × TR ΔE 12,3, × decisivo ΔE 18,7 (pior visão) |
| Pior par daltônico, gráficos | 14,5 (TR × decisivo) | 12,3 (TR × decisivo) |
| Pior par daltônico, radar | não medido (molotov = TR) | 12,3 (TR × molotov) |

A nota antiga sobre o esmeralda ("não clareie o verde sem rodar o script") continua valendo como método: o verde ficou mais claro **porque** o fundo ficou escuro, e o script confirma (6,83:1 no fundo). O aviso de que "nenhuma quarta cor passa no modo escuro" para o scatter de clusters continua de pé: o scatter segue facetado.

O validador é `metrics/paleta.py` (`py -3.12 -m metrics.paleta`), que lê os tokens de `dashboard/web/tokens.css`;
a saída está fixada em `tests/fixtures/paleta_v2_saida.txt` e conferida por `tests/test_paleta_v2.py`.
