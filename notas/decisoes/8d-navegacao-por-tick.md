# Decisão 8d: Navegação do replay usa o TICK, não o tempo em segundos

- **ID:** 8d
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** O replay navega por tick; fora da janela exportada, não navega.

## Texto

8d. **Navegação do replay usa o TICK, não o tempo em segundos.** O tick é o dado
   primário; segundos são apresentação. Derivar a navegação do tempo permitiu que
   um `Math.max(0, ...)` no caminho do clique mascarasse o timestamp negativo — a
   interface ficava plausível e o dado continuava errado. Se o tick cair fora da
   janela exportada do replay, a entrada não é clicável e o motivo vai no
   `title`: melhor não navegar que navegar para o lugar errado em silêncio.
