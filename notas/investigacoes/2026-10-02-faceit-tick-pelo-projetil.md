# FACEIT: o tick da soltura pelo projétil

- **Data:** 2026-10-02
- **Decisão:** [21a](../decisoes/21a-arremesso.md)
- **Resumo:** Sem `grenade_thrown`, a ancoragem acerta o tick em 41%; o evento é reconstruível do projétil. Regra pronta e desligada à espera de aprovação.

> Narrativa da investigação, como foi registrada na época. A regra que vale hoje está na decisão.

**INVESTIGAÇÃO FACEIT (2026-10-02): hipótese CONFIRMADA, regra pronta e
    DESLIGADA à espera do Pedro** (`scripts/investiga_faceit.py`,
    `data/reference/investigacao_faceit.json`). Os neutros a mais da FACEIT
    vêm do TICK: sem `grenade_thrown`, a soltura é a da ancoragem, e nas 13
    partidas com gabarito (evento retirado de propósito) ela cai no tick do
    projétil em só 2.848 de 6.865 (41%).
    - Deslocar a ancoragem NÃO resolve (regra igual para todos): t-1 rotula
      2.604 de 3.020 na FACEIT (hoje 2.486) mas tira o botão de 168; t+1 piora
      (2.181). Nenhuma regra troca botão, e no controle nenhuma erra o botão
      lido (rotulados = certos em todas).
    - A regra que fecha é outra: o evento é RECONSTRUÍVEL. Nas 43 partidas com
      evento (20.863 solturas): tick do evento = tick do primeiro ponto do
      projétil em 100%; mira e pés do evento = tabela de ticks em t-1 em 100%
      (20.862; 1 sem o tick). Com o evento retirado e reconstruído
      (`evento_pelo_projetil`, `fonte_tick` "projetil"), 20.862 de 20.863
      arremessos saem com números idênticos aos do evento real.
    - Efeito na FACEIT com a regra ligada (medido, depois revertido): botão em
      2.920 de 3.020 (hoje 2.486); neutros por tolerância 124 -> 16, guarda do
      voo 208 -> 23, janela 0-5 141 -> 0. Biblioteca contra o main: piora 0;
      447 ganham botão; 17 neutros por regra; 6 entram, 22 saem (reprodução
      exata reavaliada no tick certo); 2.390 comandos mudam, só nas 9 de
      FACEIT. compara_capturas idêntico.
    - POR QUE NÃO FOI LIGADA: dois testes existentes de test_grenade_throws.py
      afirmam o comportamento antigo (`test_sem_evento_oficial_a_ancoragem_
      continua_valendo` e `test_a_ancoragem_acha_o_tick_da_soltura_e_nao_o_do_
      clique`). Ligar = `TICK_PELO_PROJETIL_SEM_EVENTO = True`, ajustar os dois
      com aprovação, `VERSAO_DAS_METRICAS` 12, reprocessar e regerar a
      biblioteca. A premissa na FACEIT (o primeiro ponto do projétil é o tick
      da soltura) não tem evento para conferir lá; a evidência é a identidade
      nas 43 e os neutros da FACEIT caírem no mesmo padrão do controle.
