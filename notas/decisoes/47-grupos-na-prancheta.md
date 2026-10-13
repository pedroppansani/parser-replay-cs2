# Decisão 47: Grupo na prancheta é transporte do log; quem pode desenhar, o servidor decide

- **ID:** 47
- **Status:** vigente
- **Data:** 2026-10-13
- **Resumo:** Um grupo (sala do Supabase) só transporta as operações do log da prancheta, na ordem total de sempre; nenhuma muda de significado. A permissão de desenhar é do servidor (RLS); a tela espelha e, na recusa, tira a operação do log local e diz o motivo. Sem grupo, nada muda e nada vai para a rede. Desligado (`GRUPOS_ATIVOS = False`) até a revisão de segurança.

## Texto

47. **Grupo na prancheta é transporte do log; quem pode desenhar, o servidor decide** (fase 13,
2026-10-13).

- **Transporte, não estado.** A sala (`dashboard/web/sala.js`) leva e traz operações; quem aplica é a
  prancheta, pela ordem (Lamport, autor, id) da decisão 32. A coluna `lamport` é o `seq` da própria
  operação; `(sala, autor, lamport)` e o id da operação são únicos, então nada entra duas vezes.
  Desfazer continua sendo `anula`/`reativa` do próprio autor: no grupo, o autor da operação é o nick da
  sala (único na sala, sem diferença de caixa), e a pilha de desfazer começa vazia ao criar ou entrar.
- **Permissão no servidor.** As políticas estão em `supabase/migrations/`; a revisão em
  `notas/seguranca/grupos.md`. A tela é otimista: aplica, envia e, se o servidor recusar (sem
  permissão, encerrada, ritmo, 8 KB), tira a operação do log LOCAL -- ela nunca esteve no log da sala --
  e a linha de dica diz o motivo. Não se emite `anula` para isso: a anulação também seria recusada.
  "Desenhar" é qualquer operação, inclusive as da fase 11 (`desenha_granada`, `define_area_desenho`).
- **Ganchos mínimos na prancheta.** `tactics.js` só ganhou `Prancheta.ganchos` (autor, aoEmitir,
  aoMudarTempo, aoAtualizar, aoIniciar, dica, abas) e `Prancheta.grupo` (recebe, retira, usaDocumento,
  cabecote, segueCabecote, limpaHistorico). Sem grupo nenhum gancho é preenchido.
- **Reconexão.** Ao voltar, a pessoa busca as operações com Lamport acima do último que recebeu E as
  gravadas desde 60 s antes da última recebida (`FOLGA_DA_RECONEXAO_MS`). Só o Lamport não basta: uma
  operação de quem estava atrasado tem Lamport menor e pode chegar depois. A repetida não entra (id).
  O que a pessoa fez caída fica numa fila e sai quando a conexão volta.
- **Seguir a líder** é ligado por padrão para membro. A líder anuncia o cabeçote e o play por Broadcast
  (no máximo a cada 120 ms; tocando, a cada 1 s para corrigir a deriva); mexer no cabeçote por conta
  própria solta, e "Voltar para a líder" religa.
- **Sem grupo, nada muda.** O botão só existe com `GRUPOS_ATIVOS`, URL e chave pública
  (`scripts/grupos_config.py`); sem isso a página é byte a byte a do build sem grupo. Com o botão,
  nenhum pedido de rede até "Criar grupo" ou "Entrar": o supabase-js (versão exata, sha256 conferido
  pelo build) é carregado por script dinâmico só aí.
- **Arquivo local (`file://`).** Com a sala falsa, o grupo funciona aberto como arquivo (é como os
  testes rodam). Com o Supabase real não deu para conferir sem o projeto (origem nula no login anônimo
  e no Realtime), então, aberta como arquivo, a aba mostra "Grupos funcionam no site publicado" com o
  link (`GRUPOS_NO_ARQUIVO_LOCAL = False`). A parte B confere; se funcionar, a constante vira `True`.
- **Tática que não vira grupo:** a que tem operação acima de 8 KB (o caminho de um jogador com muitos
  pontos; 3 dos 1.152 rounds do corpus, medidos no texto do jsonb) e a que junta cópias de mais de uma
  pessoa com números de ordem repetidos (o par autor + lamport precisa ser único). A tela diz por quê.
- **O link** é `prancheta_<mapa>.html#sala=CODIGO` (as páginas são uma por mapa; o pedido falava em
  `prancheta.html?mapa=…`).
- **O convite vale para o mapa da sala** (fase 12b). A sala guarda o mapa (`salas.mapa`); quem não é membro
  não lê `salas`, então a página descobre o mapa pela própria `entrar_na_sala`, que já devolvia `mapa`
  (nenhuma migração mudou; o SQL de `notas/seguranca/grupos.md` segue igual ao das migrações). Se o
  mapa da sala não é o da página (código colado em "Entrar num grupo", ou `#sala=` aberto na página de outro
  mapa, seguido do clique em "Entrar"), a página guarda o nick e vai para `prancheta_<mapa>.html#sala=CODIGO&nick=NICK`;
  lá a entrada recomeça sozinha (só nesse salto, com o nick no link) e é idempotente: quem já é membro volta
  sem recontar nick nem o limite de 10. O nick sai da barra ao entrar. O mapa vindo do servidor só vira
  endereço se casar com o check de `salas.mapa`; no destino, mapa ainda diferente mostra aviso (nunca em laço).
  Abrir um link `#sala=` sem nick continua não fazendo pedido nenhum: só o clique entra. Para os testes, a
  `SalaFalsa` pode compartilhar o servidor entre páginas do mesmo navegador (`falsa.compartilhado`, localStorage).
