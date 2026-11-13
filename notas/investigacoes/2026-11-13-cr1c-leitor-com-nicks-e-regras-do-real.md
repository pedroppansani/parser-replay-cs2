# CR1c: o leitor com os nicks e as regras do round real (sem tela)

Terceira fase da CR1 (proposta em `2026-11-13-comandos-no-reescrever-cr0.md`). Sem tela: nenhum arquivo do site carrega o módulo novo ainda (a CR2 o liga ao painel). A prancheta lê exatamente como antes.

## O que mudou
- **`comandos/leitor.js`** (compartilhado com a prancheta, que o traz embutido): passou a entender **nicks**, mas só quando `ctx.jogadores[i].nick` existe; sem isso nada novo roda.
  - o nick vale como sujeito (`achaNicks`), pelo mesmo mecanismo dos nomes de lugar (a chave de palavras: "donk666" e "DONK 666" valem o mesmo), **sem diferenciar caixa nem acento** (a `norm` do leitor);
  - o **parcial** só com **4 letras ou mais**, prefixo de uma **palavra do nick**, **único** entre os jogadores e que **não seja palavra do leitor** (verbos, granadas, preposições, "meio" da fala...) **nem nome de lugar**; o nick inteiro ganha do parcial; parcial que serve a dois jogadores vira a pergunta "De qual time é...?" com os dois;
  - o nick que **também é nome de lugar** do mapa (FalleN e Niko no Dust2) **sempre pergunta**, antes de ler o resto da frase: `quem_ou_lugar`, com [o jogador (CT 2)] e [o lugar do mapa]; a decisão volta em `ctx.decisoes[chave]` e a frase é relida (uma pergunta por vez, se houver mais de uma menção);
  - "o 4" e "jogador 4" sem lado continuam perguntando sempre (`quem_lado`).
- **`comandos/real.js`** (novo, puro): `ComandosDoReal`.
  - `contexto(ctxMapa, round, t0, R)`: o **elenco** do round na ordem das colunas do banco ("TR 2" = o segundo TR), com nick, vida no instante, hora e autor da morte real, e o plant (`plant_s`);
  - `le` / `responde` / `horario` em volta do leitor: os rótulos das perguntas de "quem" levam **nick e vida** ("yuurih · CT 4", "flameZ · TR 4, morto às 1:42, antes de 1:20"); a pergunta do horário ganha o botão **"No instante (1:20)"**; e a pergunta **"bomba ou round?"** só aparece quando o horário escrito **cai depois do plant** e cabe no relógio da bomba (ex.: o plant do round 23 foi aos 79,5 s; "0:30" = 85 s no relógio do round e 89,5 s no da bomba);
  - `veredictos(leitura, ctx, fins)`: o que o round real diz de cada comando (por ação e jogador):
    - `comeca_depois_da_morte` — **recusado**: o comando começa depois da morte real; [Escolher outro jogador] e [Corrigir]. O texto traz a morte (autor e hora) e "o site não refaz esse duelo".
    - `termina_depois_da_morte` — **aplicado**, com aviso: começa antes da morte e termina depois; a peça anda até a hora da morte e **esmaece ali** (`esmaece_em_s`); sem botão de recusa. O fim vem do próprio comando ("em 8 s", "espera 5 segundos") ou do plano (`fins`, que a CR2 entrega).
    - `ja_morto` — recusado: o jogador já estava morto no instante; os mesmos dois botões.
    - `antes_do_instante` — recusado: o real não muda antes do "Reescrever daqui"; [Começar em 1:20] e [Corrigir] (`comecarNoInstante`).
    - `ok` e `pendente` (há pergunta aberta, ou o horário é "depois"/"junto", que o plano calcula).
    - precedência: `ja_morto` > `antes_do_instante` > `comeca_depois_da_morte` > `termina_depois_da_morte`.
  - `escolherOutro`: [Escolher outro jogador] tira o jogador recusado e a pergunta "quem?" volta, com todos os rótulos.
- **`scripts/comandos_contexto.py`:** `contexto_do_real(mapa)` (o contexto do mapa sem jogadores, com os textos do real) e `TEXTOS_DO_REAL` (relógio da bomba, elenco, vereditos e botões). Os **três textos do nick que também é lugar** ficaram no `TEXTOS` comum, porque o leitor é o mesmo nas duas telas e um teste da C1 exige que todo texto do leitor esteja nele (a página da prancheta ganha 3 textos que não usa).

## Os 10 exemplos do round 23 da match_43 (testes)
"Reescrever daqui" em 1:20 (quadro 140). Todos viram teste em `tests/test_comandos_do_real.py` com os dados reais (`replay.json`):
1. "ZywOo roda pra B aos 0:50": `comeca_depois_da_morte` (ZywOo morre para molodoy às **0:52**; a tela trunca os segundos, a CR0 dizia 0:53 por arredondar), [Escolher outro jogador] [Corrigir].
2. "o 4 joga smoke no janelão aos 1:05": pergunta "De qual time é 'o 4'?" com `yuurih · CT 4` e `flameZ · TR 4, morto às 1:42, antes de 1:20`; yuurih dá `ok`, flameZ dá `ja_morto`. (A granada que ele não jogou é a regra da CR3.)
3. "FalleN joga smoke no janelão aos 0:57": CT 2, sem pergunta (no Mirage "FalleN" não é lugar); `ok`.
4. "ropz e apEX correm pro meio aos 1:10": dois `ok`.
5. "mezii segura a caverna até 0:45": `ok`. **Achado:** a tabela da CR0 dizia "começa em 1:20 e fica até 0:45", mas o leitor (o da prancheta) lê o horário de "segura X até H" como o do comando, e a CR1c mantém essa leitura; se o Pedro quiser "até" como fim, é decisão do leitor também da prancheta.
6. "ropz vai pro B e depois pro meio": perguntas "Quando começa?" (com [No instante (1:20)]) e "O que o jogador faz?" para "pro meio".
7. "YEKINDAR corre pro meio aos 1:30": `antes_do_instante`, [Começar em 1:20] [Corrigir]; o botão vira 35 s do início e dá `ok`.
8. "flameZ roda pra A aos 1:15": `ja_morto`; [Escolher outro jogador] devolve a pergunta com os 10 rótulos.
9. "molodoy corre pro B aos 0:40": `comeca_depois_da_morte` (morreu para apEX às 0:47).
10. "KSCERATO corre pro meio aos 0:30": pergunta "0:30 é o relógio da bomba ou o do round?" com `89,6 s do início` e `85 s do início`; cada resposta dá `ok`.

## Os ajustes do Pedro (testes próprios)
- **Duas mortes inconfundíveis:** `test_comeca_depois_da_morte_e_recusado...`, `test_termina_depois_da_morte_e_aplicado...`, `test_os_dois_vereditos_de_morte_sao_inconfundiveis` (códigos, `aplica`, botões, textos e `esmaece_em_s` diferentes; também sem autor da morte), `test_o_fim_que_o_proprio_comando_diz_decide...` e a precedência.
- **Regras de nick da CR0:** caixa (4 grafias), acento (5 grafias de "João"), parcial com 4+ letras (zywo, yeki, kscer, falle, moloD), parcial de 3 letras ou menos nunca vale (zyw, mez, ker, yek, fal), parcial ambíguo pergunta com os nicks nos botões, nick inteiro ganha do parcial, o parcial não vale se é palavra do leitor ("molo") ou nome de lugar ("meio"), nick com número e hífen com ou sem espaço, "o 4" sempre pergunta, e FalleN/Niko no Dust2 sempre perguntam (uma pergunta por vez; "lugar" leva ao ponto do Pedro).

## A prova de que a prancheta continua idêntica
1. **Testes da C1 a C4 sem mudança** (`test_comandos_leitor`, `_aba`, `_documentados`, `_granada`, `_tempos`, mais `test_plano_dos_comandos`, coerência e fontes): **190 passaram** junto com os 56 novos, nenhum arquivo de teste alterado.
2. **O leitor, byte a byte** (`scripts/design/prova_leitor_dos_comandos.py`, no `node`; 4 mapas, 360 frases da gramática + 27 à mão por mapa, cada resposta a cada opção, 12 horários; contexto da prancheta, sem nicks): **1.548 leituras, 502 respostas, 48 horários iguais**, 0 diferentes, hash geral igual antes e depois.
3. **A prancheta de ponta a ponta** (a bateria da CR1a, no navegador: 4.068 frases, 1.080 buscas de granada real, 48 caminhos de tela): **todas iguais** às gravadas antes da CR1a, mesmas contagens por ramo.
4. **O site gerado** (`build_site` no `main` e na branch): 141 arquivos nos dois; mudaram só as **10 pranchetas** (cada uma +5,4 KB: o leitor passou de 32.702 para 37.415 bytes, mais os 3 textos); os outros **131 são idênticos byte a byte**. O `real.js` não entra em nenhuma página (a CR2 o liga).
