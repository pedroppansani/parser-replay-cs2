# Decisão 7g: IGL nunca é atribuído automaticamente

- **ID:** 7g
- **Status:** vigente
- **Data:** 2026-09-19
- **Resumo:** IGL nunca é atribuído automaticamente; vem de `roles_manual.json`.

## Texto

7g. **IGL nunca é atribuído automaticamente.** O áudio EXISTE no demo
   (`parse_voice` devolve 124–162 mil pacotes por partida, nas 9), mas sem
   transcrição só dá para medir TEMPO DE FALA — e tempo de fala não acha o
   capitão: medido, o jogador com 32% de toda a voz de uma partida era o astro
   do time, não quem chamava. O rótulo vem de `roles_manual.json`, preenchido à
   mão, e há teste que falha se o código escrever nesse arquivo.
   `pesquisa/igl_candidatos.py` ranqueia CANDIDATOS por time com cinco proxies
   (doa arma, compra menos que o time, contato tardio, granadas por round,
   rating baixo), cada um comparado dentro do time, com aviso de confiança
   baixa. Só imprime; há teste garantindo que ele não escreve nada.
   Medido contra o gabarito do Pedro (`data/reference/igl_conhecidos.json`, 43
   partidas, 2026-09-19): a média dos cinco acerta o IGL em 5 dos 6 times com
   gabarito. Os proxies mais fortes são **"compra menos que o time"** e
   **"granadas por round"** -- sozinhos, o IGL nunca fica abaixo do 2º lugar.
   Isso é informação sobre o PAPEL, não só sobre a métrica: o IGL compra por
   último e joga a utility da execução.
   **VIÉS CONHECIDO, e não é ruído:** os proxies descrevem um ESTILO de IGL --
   o que fragga menos, compra menos, entra depois. IGL agressivo, que lidera
   entrando na frente, é invisível para eles e sai sistematicamente rebaixado.
   O caso é o apEX: IGL confirmado da Vitality, aparece em 4º, atrás do mezii.
   Não foi corrigido de propósito -- saber onde a métrica falha vale mais que
   uma correção chutada.
