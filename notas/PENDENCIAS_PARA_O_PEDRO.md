# Pendências para o Pedro

Um cartão por decisão em aberto. Cada um dá para responder sem abrir outro arquivo. Os números
vêm das medições citadas em cada cartão. Atualizado em 2026-10-05, depois das fases 7, 8 e 9.

As tarefas dentro do jogo ficam em [`PENDENCIAS_NO_JOGO.md`](../PENDENCIAS_NO_JOGO.md), e só
entram aqui quando uma decisão depende delas.

---

## 1. Dano de utilidade e assistência de flash na escada de validação

- **Origem:** fase 7, item 7.2 (validação das métricas de impacto). Escada em
  `scripts/escada_validacao.py`.
- **Pergunta:** as assistências de flash e o dano de utilidade viram degraus da escada, conferidos
  contra a HLTV?
- **O que já existe:** os "Detailed stats" que você já colou (setembro) trazem a coluna A (f), de
  assistências de flash. Ela está transcrita por mapa, em 74 linhas de
  `data/reference/brutos/hltv_detalhado_por_mapa_2026-09-22.tsv`. O dano de utilidade não aparece
  em nenhum dos prints colados.
- **Opções:**
  1. **Só a assistência de flash agora.** É um degrau novo de contagem exata por série, sem nada de
     você. A tela não muda; muda o relatório da escada.
  2. **Os dois.** Além do 1, você manda o print da HLTV que mostra o dano de utilidade por
     jogador, se a HLTV publicar esse número nas estatísticas da partida.
  3. **Nenhum.** As métricas de utilidade continuam validadas só por invariantes no corpus (dano de
     utilidade ≤ dano total; cegueira ≤ duração × 5).
- **Recomendação:** a 1 já, e a 2 se a página existir. A 1 não custa nada e testa a ligação entre
  flash e kill, que hoje não tem gabarito.
- **Custo de deixar como está:** "kills em inimigo cego por flash" e "dano por HE/molotov"
  continuam na tela sem conferência externa.
- **Fora do computador:** só para a opção 2. Abra a página de estatísticas de uma das partidas
  HLTV do corpus (por exemplo, NAVI x Spirit em Katowice) e veja se há uma coluna de dano de
  utilidade. Se houver, mande o print dela para as 13 partidas com HLTV.

## 2. `EXIGE_FUNCAO_ACIMA_DO_ACASO`

- **Origem:** decisão 39; `metrics/structural_roles.py`; medição em
  `pesquisa/funcao_acima_do_acaso.py`.
- **Pergunta:** a função dominante de um jogador num lado só aparece quando é improvável que tenha
  saído do acaso (binomial, alfa 0,05)?
- **Opções:**
  1. **Ligar.** Tira a função dominante de 324 dos 730 jogador-lados. O lado TR quase some (251 →
     48: entry 70 → 7, lurker 33 → 1, trader 44 → 4), e 82 dos 166 AWPers perdem o rótulo. Os cards
     de função e o "sem função dominante" mudam em muitas páginas.
  2. **Deixar desligado** (hoje). A chance ao acaso é gravada e não muda nada na tela.
  3. **Ligar só como aviso.** A função continua, com "(pode ser acaso)" quando a chance passa de
     0,05. Muda texto, não rótulo.
- **Recomendação:** a 3. Com 12 rounds por lado, o teste exige 6 de 12 no TR e 7 de 12 no CT, o
  que é rígido demais para uma partida só. Apagar quase todo o TR tira mais leitura do que
  protege. O aviso diz a verdade sem esvaziar a tela.
- **Custo de deixar como está:** funções dominantes que podem ser acaso aparecem sem nenhuma
  marca. O "tendência" da decisão 39 cobre os rótulos de traço, não a função estrutural.
- **Fora do computador:** nada.

## 3. A variante do agrupamento de estilos (auditoria 4.7)

- **Origem:** auditoria, item 4.7 (tempo até o contato nulo quando não há contato; decisão 17 da
  versão das métricas).
- **Pergunta:** fica a variante adotada, em que a coluna `sem_contato` existe mas não entra no
  agrupamento?
- **Opções:**
  1. **Manter a adotada.** A concordância com os grupos anteriores fica em ARI 0,936, e os nomes dos
     grupos foram remapeados. A tela de Estilos fica quase igual.
  2. **`sem_contato` como feature do agrupamento.** O ARI cai para 0,652: um terço dos rounds muda
     de grupo, e os grupos passam a separar "teve contato ou não" mais do que estilo.
- **Recomendação:** a 1. Ter contato ou não é resultado do round, não estilo de jogo (decisão 7b:
  só comportamento entra no agrupamento).
- **Custo de deixar como está:** nenhum na tela. Só falta o seu "ok" para fechar o item.
- **Fora do computador:** nada.

## 4. As 289 tendências

- **Origem:** decisão 39 (estabilidade dos rótulos por reamostragem, limiar 0,70).
- **Pergunta:** 289 dos 531 rótulos de traço saem com "(tendência)". Isso é o que você quer ver, ou
  o limiar está alto demais?
- **Números:** AWPer 7 de 94 são tendência; Lurker 46 de 56; Segundo homem 33 de 39. O rótulo
  principal de 167 dos 358 jogadores com rótulo é tendência.
- **Opções:**
  1. **Manter 0,70** (o valor do texto da auditoria). Mais da metade dos rótulos sai com a marca.
  2. **Baixar o limiar** (por exemplo, para 0,60). Menos rótulos com a marca, mais rótulos
     afirmados que mudam ao reamostrar os rounds.
  3. **Esconder em vez de marcar.** O rótulo abaixo de 0,70 não aparece. A tela fica com menos de
     metade dos rótulos.
- **Recomendação:** a 1. Lurker e Segundo homem são leituras de poucos rounds por partida. Que
  sejam tendência é o achado, não um defeito. Mudar o limiar só faria a tela afirmar mais do que
  o dado sustenta.
- **Custo de deixar como está:** a tela parece hesitante nesses dois rótulos. O número está certo.
- **Fora do computador:** nada.

## 5. `TICK_PELO_PROJETIL_SEM_EVENTO` (demos da FACEIT)

- **Origem:** `metrics/grenade_throws.py`; medição em `pesquisa/investiga_faceit.py`.
- **Pergunta:** nas demos sem o evento `grenade_thrown` (as da FACEIT), o tick da soltura passa a
  sair do primeiro ponto do projétil?
- **Números:** nas 43 partidas que têm o evento (20.863 solturas), o tick do evento é o do primeiro
  ponto do projétil em 100% dos casos. A ancoragem usada hoje acerta só 41%.
- **Opções:**
  1. **Ligar.** A biblioteca de arremessos é regerada: 447 botões a mais, 2.390 comandos da FACEIT
     mudam e nenhum piora. Sobe a versão das métricas, com reprocesso. Muda o que dois testes de
     `test_grenade_throws.py` afirmam, e a migração deles precisa de autorização.
  2. **Deixar desligado** (hoje). As demos da FACEIT continuam com o tick pela ancoragem.
- **Recomendação:** a 1. É medição direta (100% contra 41%), e os comandos de console da FACEIT
  hoje saem do tick errado em mais da metade dos casos.
- **Custo de deixar como está:** os arremessos das partidas FACEIT da prancheta têm o comando de
  console menos confiável.
- **Fora do computador:** nada. Se quiser conferir, rode no jogo dois comandos da FACEIT que
  mudam (fica por último).

## 6. Os pontos da rota B

- **Origem:** "Pontos de calibração" no `CLAUDE.md`; decisão 21a;
  `notas/investigacoes/2026-09-28-rota-b.md`.
- **Pergunta:** três valores lidos da demo pela rota B: a força intermediária, o agachamento parcial
  e o custo da tabela `movimento`.
- **Opções, por ponto:**
  - **Força intermediária:** a força 0,6141 afirma "médio" (o botão do meio do arremesso). Aceitar
    faz a ficha afirmar o botão nesses arremessos. Recusar deixa-os neutros.
  - **Agachamento parcial:** hoje é neutro (a ficha não diz se estava agachado). A alternativa é
    arredondar para agachado ou em pé, o que afirmaria uma postura que a demo não fixa.
  - **Custo da tabela `movimento`:** é o peso do interim das partidas com `.dem`. Manter dá a
    postura lida; cortar volta a inferir pela rota A.
- **Recomendação:** aceitar a força 0,6141 como "médio", porque é o valor que o jogo grava para o
  botão do meio. Manter o agachamento parcial neutro (decisão 21a: nunca um palpite). Manter a
  tabela `movimento`.
- **Custo de deixar como está:** os arremessos com força intermediária ficam sem botão na ficha.
- **Fora do computador:** só se quiser conferir a 0,6141. Jogue um arremesso com o botão do meio
  no jogo e grave a demo (fica por último).

## 7. Os cinco `.rar` em `demos/entrada/`

- **Origem:** regra 36 (preservação de dados); `RECUPERACAO_DEMOS.md`.
- **O que são:** cinco pacotes, com 4,4 GB no total. São a ÚNICA cópia das demos de 12 partidas
  processadas, cujos `.dem` já foram apagados (o manifesto marca `existe: false`). As pastas em
  `demos/entrada/_extraido/` estão vazias.

  | pacote | tamanho | partidas |
  |---|---|---|
  | iem-cologne-major-2026-natus-vincere-vs-spirit | 0,47 GB | match_10, match_11 |
  | iem-krakw-2026-falcons-vs-mouz | 1,14 GB | match_41, match_42 |
  | iem-rio-2026-furia-vs-vitality | 0,69 GB | match_12, match_14 |
  | iem-rio-2026-natus-vincere-vs-furia | 0,92 GB | match_15, match_16, match_17 |
  | pgl-cluj-napoca-2026-furia-vs-falcons | 1,14 GB | match_18, match_19, match_20 |

- **Pergunta:** o que fazer com eles?
- **Opções:**
  1. **Manter onde estão** (hoje). Nada muda.
  2. **Extrair e complementar.** Extrair os `.dem` e rodar `scripts/complementa_interim.py`: as 12
     partidas ganham as tabelas da rota B (força, velocidade e postura lidas), e o gabarito de
     arremessos cresce de 13 para 25 partidas. Depois, os `.dem` extraídos seguem a regra 36.
  3. **Apagar.** Só com lista confirmada e outra cópia conferida por hash (regra 36). Hoje não há
     outra cópia conhecida.
- **Recomendação:** a 2. É o maior ganho disponível para a rota B sem baixar nada.
- **Custo de deixar como está:** 12 partidas continuam com a postura e a força inferidas, em vez de
  lidas.
- **Fora do computador:** nada. A extração roda aqui, e o disco precisa de cerca de 10 GB livres
  durante ela.

## 8. As branches

- **Origem:** "manter todas as branches"; resposta 7. Nenhuma é apagada sem a sua confirmação.
- **Pergunta:** quais destas, já mescladas, você quer apagar? Ou mantém todas?
- **Lista (hash local / no GitHub / conteúdo no main):**

  | branch | hash | no GitHub | conteúdo no main |
  |---|---|---|---|
  | fase-1-correcoes | 95c18700 | 95c18700 | sim |
  | fase-2-vitrine | c27b9353 | c27b9353 | sim |
  | fase-3-claude-md | cc4ce459 | cc4ce459 | sim |
  | fase-4-rigor | f944da2c | f944da2c | sim |
  | fase-5-acabamento | 0e13ea9c | 0e13ea9c | sim |
  | **fase-6-decisivo** | 65baf1ba | 65baf1ba | **NÃO: 3 commits fora (6.1 a 6.3), esperando as suas respostas** |
  | fase-7-metricas | 8ac55198 | 8ac55198 | sim |
  | fase-8-prancheta-tempo | 0bc43b37 | 0bc43b37 | sim |
  | fase-8a-clique | 0bb7c9fd | 0bb7c9fd | sim |
  | fase-9-round-na-prancheta | fbf63ffc | fbf63ffc | sim |
  | investigacao-faceit | 7adc84f5 | só local | sim |
  | prancheta-fluida | 7de4f46b | 7de4f46b | sim |
  | rota-a-em-andamento | 068c578c | 068c578c | sim |
  | rota-b | 53d9bf84 | só local | sim |

  "Sim" quer dizer que o último commit da branch é ancestral do main: tudo o que ela tem está no
  main. As tags `baseline-antes-auditoria` e `baseline-antes-fase-6` não entram nesta lista e
  nunca são movidas.
- **Recomendação:** apagar as mescladas, menos a `fase-6-decisivo`. O histórico fica inteiro no
  main e nas tags.
- **Custo de deixar como está:** nenhum, só a lista longa.
- **Fora do computador:** nada.

## 9. O item 5.8 da auditoria: arquivos grandes

- **Origem:** auditoria, "Arquivos grandes". O template tem uma função de cerca de 88 KB que monta
  HTML por concatenação, e o `tactics.js` passou de 2.449 para cerca de 3.900 linhas com as fases 8
  e 9.
- **Pergunta:** dividir agora o JS do template por aba e o `tactics.js` por assunto (modelo,
  linha do tempo, round real), ou só quando for mexer em cada parte?
- **Opções:**
  1. **Agora**, numa fase só de refatoração, com o `compara_capturas` exigindo pixel idêntico. A
     tela não muda.
  2. **Quando for mexer** (o texto da auditoria). Cada fase que tocar uma aba a separa.
- **Recomendação:** a 1, antes do design (`PROMPT-implementacao-design.md`). O design vai mexer em
  todas as abas, e separar antes deixa cada mudança visual menor e revisável.
- **Custo de deixar como está:** cada mudança de tela continua acontecendo dentro de arquivos de
  milhares de linhas, com conflitos entre fases.
- **Fora do computador:** nada.
