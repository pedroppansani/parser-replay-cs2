# O que falta: lista do Pedro

Atualizada em 21/10/2026. Marque com `x` o que for fazendo.

## Feito

- [x] **Iriun:** design v2 fechado, respostas de segurança registradas e nenhuma rotina criada.
- [x] **Projeto (CS2 Parser):** prompt mestre e respostas da v2-0 colados; o Code está seguindo a fila.

## Supabase (para liberar a parte B dos grupos)

- [x] **Push protection no GitHub:** abra o repositório `parser-replay-cs2` → **Settings** → **Advanced Security** (em algumas contas aparece como "Code security") → em **Secret Protection**, ligue **Push protection**. Ele bloqueia um push que tenha uma chave secreta por engano.
- [x] **Alerta de uso no Supabase:** conferido (Free Plan, uso quase zero). abra a organização `parser-cs2-grupos` → **Usage**.
  - No plano Free, sem cartão, não existe cobrança: se passar do limite, o projeto é pausado, e o Supabase avisa por e-mail.
  - Confira só se o e-mail da conta é um que você lê.
  - Se aparecer uma opção de alerta de uso, ligue. Se não aparecer, está ok assim.
- [ ] **Avisar o Code.** Cole:
  > Supabase conferido: Push protection ligado no GitHub e plano Free sem cartão. O projeto parser-cs2-grupos está PAUSADO por inatividade (plano Free pausa depois de 7 dias sem uso); eu reativo quando a parte B começar. A ordem não muda: a parte B fica para depois da v2-7. Registre no `estado-atual.md`: (1) parte B destravada, mas antes de começar ela você me pede para reativar o projeto e espera eu confirmar; (2) pendência para a revisão de segurança: no Free o projeto pausa depois de 7 dias sem uso, então os grupos no ar podem parar se ninguém usar; isso precisa de uma decisão antes de ligar o GRUPOS_ATIVOS.
- [ ] **Reativar o Supabase só quando a parte B começar:** botão **Resume project** (dá para reativar até 23/11/2027). Não clique em **Upgrade to Pro**.
- [ ] **Depois da parte B:**
  - baixar o limite de login anônimo para 10 (Authentication → Rate Limits);
  - levar o `grupos.md` atualizado ao agente de segurança do Iriun. Eu faço o prompt quando chegar a hora.

## Quando o Code pedir

- [x] **3 exemplos novos de "flash no time":** respondidos (sim nos 3).
- [x] **Plano da v2:** respondido. Colar o `PROMPT-respostas-v2-0-e-pendencias.md` na sessão do projeto.
- [ ] **Qualquer parada com "escolha do Pedro":** me manda o texto.

## Quando você puder (sem pressa)

- [ ] **Teste do console no CS2** (seção 4 do material de calibração): servidor local na Mirage, colar dois comandos e ver se a smoke cai no ponto do preview. Uns 5 minutos.
- [ ] **Teste com o NVDA** (o leitor de tela), seguindo o roteiro que o Code escreveu na §7.3.
- [ ] **Round decisivo** (§6, branch `fase-6-decisivo`): responder as perguntas pendentes do material dele.
- [ ] **Prints da HLTV** para o cartão 1 (o dano de utilidade): as páginas de estatística das partidas que o cartão lista.
- [ ] **Ângulos da Nuke** (seção 5 do material de calibração, 38 linhas): é o mais trabalhoso e pode ficar por último.

## Depois de tudo

- [ ] **Investigação do awpy 3:** abrir uma sessão separada, na pasta `awpy-v3-teste`, e colar o `PROMPT-investigar-migracao-awpy-v3-PARA-DEPOIS.md`. Só quando a calibração, os grupos e a fase 6 estiverem fechados.
- [ ] **Rotinas do Iriun** (YouTube, deploy/segurança e a semanal do design): ligar só se quiser, depois que a v2 estiver no ar.
