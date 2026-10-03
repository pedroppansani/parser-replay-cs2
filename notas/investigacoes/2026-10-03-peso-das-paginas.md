# Peso das páginas da partida (auditoria, item 5.5, 2026-10-03)

O item pedia gravar o JSON injetado com `separators=(",", ":")`. Medido antes de mexer: as três
injeções grandes (`web_payload.json`, `replay.json`, `breakdown.json`) **já eram gravadas
compactas** pelo `export_web_payload` e pelo `export_replay`. Só três injeções pequenas saíam
indentadas (radar, dados da página e lista do site), e agora saem compactas também
(`scripts/json_em_script.py`, sem `compacto=False` nos builds; há teste).

| página | bruto antes | bruto depois | gzip antes | gzip depois | FCP (mediana de 5) | DOMContentLoaded |
|---|---|---|---|---|---|---|
| match_42 (a maior) | 4.864.424 B | 4.864.402 B | 999.678 B | 999.663 B | 260 → 280 ms | 325 → 350 ms |
| match_01 | 1.976.631 B | 1.976.609 B | 436.479 B | 436.463 B | 260 → 260 ms | 320 → 335 ms |
| match_06 (a menor) | 1.875.063 B | 1.875.041 B | 450.623 B | 450.606 B | 252 → 268 ms | 314 → 333 ms |

A diferença de tempo está dentro do ruído de cinco cargas (arquivo local, Chrome, 1366x768); o
ganho de 22 bytes não move nada.

**De onde vem o peso** (match_42): `replay.json` 3.964 KB (700 KB em gzip), `web_payload.json`
286 KB, `breakdown.json` 40 KB, `template.html` 145 KB, `map_core.js` 42 KB, `annotations.js`
43 KB, radar com a imagem em base64. O replay é ~82% da página. As páginas continuam
autocontidas por decisão do projeto, então o caminho para emagrecer seria o próprio replay
(amostragem de 4 Hz, casas decimais das posições), não separar arquivos -- fica registrado, não
foi feito.
