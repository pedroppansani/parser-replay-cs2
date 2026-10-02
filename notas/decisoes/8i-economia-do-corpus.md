# Decisão 8i: Economia do rating estimada no CORPUS, por arma mais cara + colete

- **ID:** 8i
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Economia do rating estimada no corpus, por arma mais cara e colete.

## Texto

8i. **Economia do rating estimada no CORPUS, por arma mais cara + colete**
   (`metrics/economia.py`, `scripts/fit_economia.py` ->
   `metrics/economia_reference.json`, refazer a cada demo nova). A versão por
   partida tinha ~20 rounds para dezenas de células e mal agia. Classe lida da
   COMPRA no fim do freeze time; colete importa (pistola inicial sem colete
   vence 4-10%, com colete ~50%). Encolhimento em dois níveis: célula com
   colete -> mesma sem colete -> taxa do lado (K = 20). Conferido contra a
   HLTV: rifle x rifle TR 49,4% (HLTV 48%); o "matar pistola inicial 75%" da
   HLTV bate com rifle contra QUALQUER pistola (75,9%), não com pistola inicial
   (96%) -- o grupo deles é mais largo que o nome. Só a taxa entra na
   conversão em peso, então a diferença de nome não a afeta. Efeito, com os
   pesos congelados: erro contra o rating oficial 0,109 -> 0,094.
