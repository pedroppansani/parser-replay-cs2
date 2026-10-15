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

## 10. Grupos na prancheta: os passos no Supabase (fases 13 e 16)

- **Origem:** fases 13 e 16, decisão 47; revisão de segurança em
  [`seguranca/grupos.md`](seguranca/grupos.md). A revisão deu BLOQUEADO em 2026-10-13; a fase 16
  corrigiu o que ela pediu (B-1, B-2, B-3 e L-1, L-2, L-3, L-5, L-6). Falta a sua parte e a parte B.
- **Pergunta:** nenhuma. Eu não crio conta, não faço login e não peço senha. As migrações, o
  cliente, os testes com a sala falsa, a aba e a documentação já estão no repositório. O botão segue
  desligado (`GRUPOS_ATIVOS = False` em `scripts/grupos_config.py`) até o veredito LIBERADO do
  `seguranca` e a sua confirmação.
- **Os passos (15):**
  1. Crie a conta em supabase.com, no plano gratuito (Free).
  2. Crie um projeto (New project) na região **South America (São Paulo)**, `sa-east-1`. A senha do
     banco fica só com você: ela não vem para o repositório nem para mim.
  3. Ligue o login anônimo: Authentication → Sign In / Providers (endereço `/auth/providers` do
     projeto) → **Allow anonymous sign-ins**.
  4. Desligue os canais públicos do Realtime: tela **Realtime Settings** → **Allow public access**
     desligado. Assim só entra no canal da sala quem o RLS deixa.
  5. Em **Settings → API Keys** (ou no botão **Connect**), copie a URL do projeto e a chave
     **publishable** (`sb_publishable_…`; a antiga se chama anon) para um arquivo `.env` na raiz do
     repositório, com duas linhas: `SUPABASE_URL=https://<projeto>.supabase.co` e
     `SUPABASE_ANON_KEY=sb_publishable_…`. O `.env` está no `.gitignore` (e os `.env.*` também). A chave
     **secreta** (`sb_secret_…`) não é usada em lugar nenhum: não copie.
  6. Instale a Supabase CLI no Windows (PowerShell):
     `scoop bucket add supabase https://github.com/supabase/scoop-bucket.git` e depois
     `scoop install supabase` (ou use `npx supabase`, que pede Node 20 ou mais novo).
  7. Rode `supabase login` você mesmo. Ele abre o navegador para você autorizar.
  8. No GitHub: Settings → Secrets and variables → Actions → aba **Variables** → **New repository
     variable**, duas vezes: `SUPABASE_URL` e `SUPABASE_ANON_KEY`, com os valores do `.env`. São
     variáveis, não segredos: são públicas por desenho. (Sem elas o build publicado não leva o host do
     Supabase na política de segurança da prancheta.)
  9. **Conferência do painel** (a condição 4 do LIBERADO). Em cada item, anote o que vê. Os caminhos
     abaixo são os da documentação do Supabase de 2026-10-14; se o painel estiver diferente, anote o
     caminho real:
     - **a.** Anonymous ligado: Authentication → Sign In / Providers → **Allow anonymous sign-ins**.
     - **b.** Email e outros provedores desligados: na mesma tela, deixe ligado só o login anônimo. A
       documentação diz que o provedor Email vem ligado por padrão
       ([auth-email](https://supabase.com/docs/guides/auth/auth-email)): desligue-o e qualquer outro
       provedor que esteja ligado. Desligar o cadastro por e-mail é o L-8 da revisão.
     - **c.** "Allow public access" do Realtime desligado: Realtime Settings (o passo 4).
     - **d.** Limite de logins anônimos por hora e por IP: Authentication → **Rate Limits**
       ([doc](https://supabase.com/docs/guides/auth/rate-limits)). O padrão é 30 por hora por IP e dá
       para mudar. Anote o valor que está lá e, se o campo deixar, baixe (por exemplo, para 10): ele é a
       única trava contra criar contas anônimas em massa.
     - **e.** Alerta de uso: a documentação que consultei não descreve um alerta de uso configurável
       no plano Free; diz só que "You will be notified when you exceed the Free Plan quota" (o aviso é
       por e-mail, depois de passar da cota). Procure no painel da organização (Usage / Billing) se
       existe algum alerta que dê para ligar e anote o que viu, inclusive "não existe".
     - **f.** O projeto está no plano Free: o plano aparece no painel da organização (Billing).
  10. **O que o plano Free faz quando passa da cota** (conferido em 2026-10-14 em
      [billing-faq](https://supabase.com/docs/guides/platform/billing-faq)): **restringe, não cobra.**
      Primeiro avisa; "If you continue to exceed the limits, service restrictions will apply": pausar
      projetos, deixar o banco só para leitura, ou responder HTTP 402 às chamadas da API, até a cota
      voltar no próximo ciclo ou até você migrar para o Pro. O limite de gasto (Spend Cap) é um recurso
      do Pro; a documentação não descreve cobrança de excedente no Free. Na tela do site, o efeito é
      "Grupo indisponível agora. A tática continua salva neste navegador."; a prancheta sozinha segue
      funcionando.
  11. **Ligue o secret scanning do repositório no GitHub:** Settings do repositório → **Code security**
      (em contas e repositórios mais antigos o menu se chama "Code security and analysis") →
      **Secret scanning** → Enable; ligue também **Push protection**. Anote o caminho real se for outro.
  12. **Me mande, no fim,** um print ou o texto de cada item da conferência (9.a a 9.f) e a confirmação
      do 11. Pode ser tudo numa mensagem só.
  13. **Me avise** que fez os passos 1 a 12. Eu rodo, na raiz do repositório, `supabase link` (escolho
      o projeto na lista que a CLI mostra) e `supabase db push` (aplica as **sete** migrações de
      `supabase/migrations/`). Se a CLI pedir a senha do banco, eu paro e quem digita é você.
  14. Eu confiro `select * from cron.job` (a tarefa `grupos-limpa-salas-antigas` tem que estar lá; B17) e
      rodo a **parte B inteira** (B1 a B19, e a medição B20 do tempo de criar um grupo do maior round):
      `py -3.12 -m pytest tests/test_grupos_integracao.py` com `GRUPOS_INTEGRACAO=1`. Cada rodada cria
      usuários anônimos reais e o Supabase limita a 30 por hora por IP. O teto global de salas (B15)
      enche o servidor e só roda com `GRUPOS_B15_GLOBAL=1`; eu aviso antes de rodar e limpo depois. Trago
      o resultado, item por item.
  15. Com a parte B passando e a conferência do painel, eu atualizo
      [`seguranca/grupos.md`](seguranca/grupos.md) (tabela de achados, resultado da parte B, o que você
      conferiu) e você o leva de novo ao agente `seguranca`. Com o LIBERADO dele e a sua confirmação
      aqui, eu mudo `GRUPOS_ATIVOS` para `True`.
- **O que o plano gratuito limita** (conferido na documentação do Supabase em 2026-10-13):
  - [Preços](https://supabase.com/pricing): 500 MB de banco, 50.000 usuários ativos por mês, 200
    conexões simultâneas no Realtime, 2 milhões de mensagens do Realtime por mês, 5 GB de saída,
    1 GB de arquivos e no máximo 2 projetos ativos.
  - [Limites do Realtime](https://supabase.com/docs/guides/realtime/limits): 200 conexões
    simultâneas, 100 mensagens por segundo, 100 entradas em canal por segundo, 100 canais por conexão,
    20 mensagens de presença por segundo e Broadcast de até 256 KB.
  - [Login anônimo](https://supabase.com/docs/guides/auth/auth-anonymous): 30 logins anônimos por
    hora por IP (ajustável no painel). A documentação recomenda CAPTCHA ou Turnstile contra abuso; não
    está ligado (fica como ponto para o `seguranca`).
  - **Os tetos que o servidor dos grupos põe por conta própria** (fase 16, medidos no maior round real
    do corpus: 68 operações e 88.835 bytes): 5.000 operações e 2 MB por sala; 300 operações por minuto e
    3.000 por hora por autor (além dos 20 por segundo); 200 salas ativas no servidor (200 x 2 MB = 400 MB,
    abaixo dos 500 MB do banco); 30 chamadas por minuto de entrar numa sala por conta. Cada teto tem a
    sua frase na tela.
  - Na prática: um grupo tem no máximo 10 pessoas, e cada pessoa ocupa 1 conexão. Cada alteração vira
    1 mensagem para cada pessoa da sala. Com 10 pessoas no teto por segundo do servidor (20 alterações
    por segundo), seriam 200 mensagens por segundo, acima das 100 do plano. O uso real (arrastar uma
    peça, traçar um caminho) fica muito abaixo disso.
- **Projeto parado por inatividade**
  ([Project Pausing](https://supabase.com/docs/guides/platform/free-project-pausing)): o plano gratuito
  pausa o projeto com pouca atividade em 7 dias, com um e-mail de aviso mais ou menos uma semana antes.
  Dá para retomar em até 1 ano no painel (organização → projeto → **Resume project**), com os dados. A
  documentação não diz o que a API responde com o projeto pausado. **Na tela:** qualquer falha ao
  criar, entrar ou enviar mostra "✕ Erro: Grupo indisponível agora. A tática continua salva neste
  navegador.", e a prancheta continua funcionando sozinha (há teste com o servidor fora do ar).
- **Limpeza:** salas paradas há 30 dias e usuários anônimos órfãos com mais de 2 dias saem por uma
  tarefa diária do pg_cron (migração 5, ampliada na 7). Se o `supabase db push` falhar só nessa
  migração, as outras bastam: rode `select grupos.limpa_salas_antigas();` no SQL Editor de vez em
  quando.
- **Custo de deixar como está:** nenhum. Sem os passos, o site continua sem o botão de grupo.

## 11. Leitor de tela na prancheta: o teste no NVDA (fase 17)

- **Origem:** fase 17. A prancheta (`dashboard/web/tactics.js`, `tactics.html`) já tem as fichas do banco
  como botões com nome e estado (`aria-label`, `aria-pressed`), os marcos de passo com nome, o resumo do
  mapa em texto (`#pr-mapa-resumo`, a descrição do canvas), as abas do painel com `role=tab` e o
  cabeçote da linha do tempo como `slider`. Eu conferi na **árvore de acessibilidade do Chrome**
  (Playwright, `Accessibility.getFullAXTree`, 2026-10-15): os nomes entre aspas abaixo são os que a
  árvore mostra. A árvore não diz o que o NVDA fala de fato nem em que ordem; isso só o teste mostra.
- **Pergunta:** o NVDA fala o que a árvore promete? Em cada passo, o que você ouviu?
- **O que a árvore mostrou:**
  - O canvas é uma imagem chamada "Mapa da prancheta", com a descrição "Às 1:55: Nenhum jogador no
    mapa."; com a ficha CT 1 no centro, "Às 1:55: 1 jogador no mapa: CT 1 em Middle.". Ele não entra
    no Tab (é imagem): o leitor chega nele pelas setas ou pela tecla G.
  - Ordem do Tab: os 5 links do topo, "MAPA" (caixa de combinação, "Mirage"), as 10 ferramentas,
    "Reproduzir a tática passo a passo", os 3 botões de zoom, "Mapa em tela cheia (F)", "Atalhos (?)",
    "Passo 1, 1:55", o cabeçote "Horário do round" (slider, valor "1:55"), "1:55" (dica "Ir para
    1:55"), "Nota: Passo 1", a aba "JOGADORES" (selecionada) e as 10 fichas, de "CT 1: colocar no
    mapa" a "TR 5: colocar no mapa", todas "não pressionado".
  - Ficha pelo teclado: o 1º Enter muda o nome para "CT 1, pronta: clique no mapa, ou Enter de novo
    para pôr no centro" (pressionado); o 2º põe a peça no centro e o nome vira "CT 1, no mapa:
    selecionar" (não pressionado). A dica de estado (região `status`, educada) passa a "CT 1
    selecionado · clique no mapa para traçar o caminho · …".
  - Cabeçote: seta para a direita anda 1 s ("1:54"), Shift+seta 5 s, Home volta a "1:55" e End vai a
    "0:00"; o resumo do mapa acompanha ("Às 1:54: …").
  - **O ponto que a árvore não resolve:** as fichas respondem a Enter/Espaço pelo `keydown` e ao mouse
    pelo `pointerup`, mas não ao evento `click` sozinho (conferi: `click()` não arma a ficha). No modo
    de navegação o NVDA ativa o botão pelo clique do próprio Chrome, e não pela tecla; se esse clique
    não gerar os eventos de ponteiro, o Enter na ficha não faz nada até você trocar para o modo de
    foco (NVDA+Espaço). O passo 7 testa os dois.
- **Antes de começar:** a tecla NVDA é o Insert (ou o Caps Lock, se você escolher na instalação).
  NVDA+Espaço troca entre o modo de navegação (as letras pulam pela página: H título, G gráfico, B
  botão) e o modo de foco (as letras vão para a página: N cria passo). O NVDA toca um som diferente
  em cada troca. O papel pode vir com outra palavra (por exemplo "botão de alternância" ou "botão
  alternar"): anote a palavra que ouvir.
- **Os passos (10):**
  1. **Instale:** baixe em [nvaccess.org/download](https://www.nvaccess.org/download/) e instale com as
     opções padrão (português vem sozinho se o Windows estiver em português). Anote a versão (NVDA+N →
     Ajuda → Sobre) e a do Chrome (`chrome://version`).
  2. **Gere e abra:** na raiz do repositório, `py -3.12 -m scripts.build_site`; com o NVDA ligado
     (Ctrl+Alt+N), abra `docs/prancheta_de_mirage.html` no Chrome. **Deve ouvir:** "Prancheta tática"
     (o título da aba, seguido de "Google Chrome").
  3. **Título e mapa:** aperte H. **Deve ouvir:** "PRANCHETA · MAPA Mirage", título nível 1 (pode
     soletrar as maiúsculas). Aperte G. **Deve ouvir:** "Mapa da prancheta, gráfico", talvez seguido de
     "Às 1:55: Nenhum jogador no mapa."; se não vier junto, aperte seta para baixo e o resumo deve vir
     como texto.
  4. **Marco do passo:** aperte Tab. **Deve ouvir:** "Passo 1, 1:55, botão".
  5. **Cabeçote:** aperte Tab. **Deve ouvir:** "Horário do round, controle deslizante, 1:55" (o NVDA
     entra sozinho no modo de foco). Aperte seta para a direita duas vezes: "1:54", "1:53". Aperte
     Home: "1:55". Anote se ele fala o horário ("1:54") ou um número ("1").
  6. **Abas:** aperte Tab até "JOGADORES, guia, selecionado" (passa por "1:55, botão" e "Nota: Passo
     1, editar"). Aperte seta para a direita. **Deve ouvir:** "GRANADAS, guia, selecionado". Seta para
     a esquerda volta a "JOGADORES".
  7. **Ficha:** aperte Tab. **Deve ouvir:** "CT 1: colocar no mapa, botão (de alternância), não
     pressionado". Aperte Enter **sem** trocar de modo e anote o que ouviu. Se o nome não mudou, aperte
     NVDA+Espaço (modo de foco) e Enter de novo. **Deve ouvir:** "CT 1, pronta: clique no mapa, ou Enter
     de novo para pôr no centro, pressionado". Anote em qual dos dois modos funcionou.
  8. **Pôr no centro:** ainda no modo de foco, aperte Enter de novo. **Deve ouvir:** "CT 1, no mapa:
     selecionar, não pressionado" e, logo depois ou um pouco mais tarde, "CT 1 selecionado · clique no
     mapa para traçar o caminho · …" (a dica de estado).
  9. **Resumo do mapa:** aperte NVDA+Espaço (volta ao modo de navegação) e depois G (ou Shift+G).
     **Deve ouvir:** "Mapa da prancheta, gráfico" com "Às 1:55: 1 jogador no mapa: CT 1 em Middle."
     (junto, ou com a seta para baixo).
  10. **Novo passo:** Tab até a ficha CT 1, NVDA+Espaço (modo de foco) e aperte N. Depois NVDA+Espaço
      (modo de navegação), G para voltar ao mapa e Tab duas vezes. **Deve ouvir:** "Passo 1, 1:55, botão"
      e "Passo 2, 1:53, botão".
- **O que anotar (por passo, uma linha basta):** o número do passo, o que ouviu (as palavras, mesmo que
  incompletas) e, se não ouviu o esperado, o que veio no lugar: nada, o nome sem o estado
  ("pressionado"), o estado sem o nome, a mensagem repetida, ou o NVDA falando a letra ("n") em vez de
  agir. No 7, diga em qual modo o Enter funcionou. No 5, se ele leu o horário ou o número. No 8, se a
  dica de estado foi lida e se cortou alguma coisa. Com a versão do NVDA e do Chrome (passo 1), isso me
  basta para corrigir.
- **Custo de deixar como está:** o que a árvore mostra está conferido; o que o NVDA fala, não. Quem usa
  leitor de tela pode não conseguir pôr uma peça no mapa (o ponto do passo 7) sem que a gente saiba.
- **Fora do computador:** nada; é tudo no Windows, com o fone ou o som ligado.
