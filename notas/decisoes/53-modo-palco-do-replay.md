# Decisão 53: Modo palco do Replay (cartão 15, opção B)

- **ID:** 53
- **Status:** vigente
- **Data:** 2026-11-04
- **Resumo:** A partir de 1024 x 600, a faixa de rounds do Replay gruda sob as abas, a página rola até o palco ao abrir o Replay ou
  trocar de round, e o mapa passa a ser quadrado com `min(100%, 640 px, 100svh - reserva)`: um tamanho só enquanto se está no Replay.
  O celular não muda.

## Texto

53. **Modo palco do Replay** (cartão 15; escolha do Pedro em 2026-11-04: opção B, com condições).

- **Faixa de rounds sempre à vista:** `position: sticky` logo abaixo das abas (que já grudam sob a navbar). Trocar de round não
  exige rolar a página.
- **Palco e colunas alinhados:** o palco (`#palco`) para logo abaixo da faixa (`scroll-margin-top`, descontado o `scroll-padding-top`
  de 86 px do `html`); as colunas dos jogadores começam na mesma linha, sem cabeçalho escondido atrás da navbar ou das abas.
- **Quando a página rola:** ao abrir a aba Replay (clique ou endereço `#replay`) e ao trocar de round pela faixa, pelo gráfico do
  Placar ou por um lance da lista. Nunca briga com a rolagem da pessoa: se ela usou roda, toque ou teclado nos últimos 500 ms, não rola.
  Com `prefers-reduced-motion` a rolagem é instantânea. Rolar não muda o layout: o CLS continua 0.
- **Um tamanho só:** a largura do mapa vem só do CSS (`--palco-reserva`, em `v2.css`), nunca do conteúdo; tocar, trocar de round,
  ligar os Lugares, trocar de andar e rolar não a mudam. Medidas: 579 px a 1440 x 900 (era 345) e 447 px a 1366 x 768 (era 231).
- **Reserva:** nav-h + 4 + abas 62 + faixa 55 + folga 8 + cabeçalho do round 55 + transporte 57 + respiro 10. As alturas são as
  medidas de hoje; `tests/test_replay_palco.py` acusa se mudarem.
- **Limite 1024 x 600** (era 700): a altura útil do Chrome num notebook 1366 x 768 é ~657 px e num 1440 x 900 é ~789 px; medidas:
  1366 x 657 = 336 px de lado, 1440 x 789 = 468 px (a conta é altura - 321).
- **Foco do teclado** (`v2.js`, `fimDasBarras`): nunca fica atrás da navbar, das abas nem da faixa de rounds, quando grudadas; o foco
  dentro de uma das barras é dela e não rola. Teste com Shift+Tab em `test_replay_palco.py`.
- **Fora do modo palco** (celular e telas baixas, menos de 1024 x 600): como antes (regra de 820/950 com reserva de 340 ou 500 px).
- **Enquadramento da Nuke (B+):** aprovado como fase SEPARADA, depois desta. Regra: o enquadramento nunca esconde jogador vivo nem
  granada; se alguém sair do quadro, o zoom abre até caber todos. (Na prévia, o "chiefkeef" aparecia cortado na borda: a fase corrige.)
- **Custo:** os 3 quadros do Replay do `compara_capturas` mudam de tamanho (520 para 640 px a 1400 x 1000); referências do PC
  regravadas em commit próprio. A prancheta não muda.
