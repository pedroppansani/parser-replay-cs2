# Prompt mestre: tudo o que falta na sessão do projeto, em ordem

Cole na sessão do Claude Code do projeto (CS2 Parser), tudo a partir da linha `---`. Se você abrir uma sessão nova e limpa, cole este prompt nela: ele traz tudo o que é preciso.

**Ele substitui o `PROMPT-resposta-tickrate-resto-divisao-claude-md.md`, que não chegou a ser colado.** Os outros prompts que ele cita continuam valendo, e o Code lê cada um no disco.

---

<como_usar_este_prompt>
Esta é a fila completa do que falta no projeto, com a ordem e as condições de cada item.

1. **Antes de começar,** confira o estado real:
   - leia o `notas/estado-atual.md`, se existir;
   - leia o `notas/PENDENCIAS_PARA_O_PEDRO.md`;
   - rode o `git log --oneline -30`;
   - pule todo item que já estiver feito e mesclado, e diga no relatório quais pulou e por quê.
2. **Os prompts citados** estão em `C:\Users\User\Desktop\Claude outputs\`. Leia cada um inteiro antes do item dele.
3. **Merge e push** depois de cada item, sem esperar confirmação, quando as condições do item forem verdadeiras. Esta autorização vale para todos os itens deste prompt, menos os que dizem "pare".
4. **Depois de cada merge,** atualize o `notas/estado-atual.md` com:
   - o que está feito, com o hash;
   - o item em andamento;
   - a fila restante;
   - as regras temporárias em vigor (por exemplo, `GRUPOS_ATIVOS=False`).

   Assim, qualquer sessão nova continua dali.
5. **Na dúvida sobre uma escolha que é do Pedro** (gosto, nome, texto do site, critério de jogo), **pare e pergunte, com opções e a sua recomendação.** Não decida por ele. As decisões técnicas com critério já escrito são suas.
</como_usar_este_prompt>

---

<item n="1" titulo="Divisão do metrics/CLAUDE.md">
**A divisão está aprovada:** o arquivo novo `metrics/erros/CLAUDE.md` (1.519 bytes) e o `metrics/CLAUDE.md` caindo para 10.674.

**Uma condição antes do merge:**

- Um `CLAUDE.md` de subpasta só é lido quando a sessão mexe em arquivos **dentro** daquela pasta. Confira onde estão os arquivos governados por essas regras: `erros.py`, os testes de erro e o gerador do material.
- **Se o código de erros estiver fora da pasta nova** (por exemplo, em `metrics/erros.py`), mova-o para um pacote `metrics/erros/` com `git mv`, com um `__init__.py` que mantenha os imports de hoje funcionando. A suíte fica verde e nenhum número muda.
- **Se mover não fizer sentido,** deixe no `metrics/CLAUDE.md` uma linha que mande ler o `metrics/erros/CLAUDE.md` antes de mexer em erros, com um teste que garanta que a linha existe.
- **O limite do arquivo novo:** 5.000 bytes, com o teste de tamanho.
- **Os blocos copiados entre pastas** continuam com marcador de origem e teste de sincronia, também no arquivo novo.

**Junto:** atualize a contagem de testes no `numeros_citaveis`. É um fato do projeto, não uma métrica de jogo, então está autorizado.
</item>

<item n="2" titulo="Calibração">
É o `PROMPT-respostas-calibracao-pedro.md`, que já foi colado nesta sessão. Se ainda não terminou, siga com ele: os pisos, os grupos e os erros, nessa ordem, cada um na sua branch.

**Uma informação nova:** a correção de flash (a7db5dc9) não afetou a calibração. A cegueira vem em segundos do evento do jogo. Não precisa refazer nada por causa dela.

**A parada que já estava prevista:** quando os três exemplos novos de "flash no time" estiverem prontos, mande-os ao Pedro e siga com o resto enquanto ele responde.
</item>

<item n="3" titulo="Os outros lugares que assumem 64 tick (fix-tickrate-resto)">
**Corrija como uma mudança sem efeito nos números.**

**O motivo:** hoje nada erra, porque as 52 partidas são de 64 tick. Mas o "Adicionar demo" vai aceitar demo de qualquer servidor, e uma de 128 quebraria sem aviso:

- o replay;
- as durações de smoke e molotov;
- a gravidade dos arremessos;
- o rating.

**As regras:**

1. **O tickrate vem da demo e é passado para baixo.**
   - O `process_demo` passa o tickrate para todas as métricas da lista que você levantou.
   - As funções deixam de ter 64 como padrão: o parâmetro passa a ser obrigatório, para quebrar na hora em vez de errar calado.
2. **Os scripts de validação e calibração** (`fit_rating`, `escada_validacao` e os de `scripts/calibracao/`) leem o tickrate do dado da partida.
3. **A prova de que nada mudou:**
   - a impressão dos números idêntica;
   - os 4 quadros do `compara_capturas` idênticos;
   - a catraca verde;
   - os arquivos de dados gerados com o mesmo sha256 antes e depois. Liste quais comparou.
4. **A prova de que funciona com 128:** para cada função corrigida, um teste com dado sintético de 128 tick que dá o mesmo resultado em segundos que o equivalente de 64.
5. **O teste que barra conversão escrita no código** esvazia a lista de pendentes. A partir daí, ele falha com qualquer literal novo.
6. **Se algum número do corpus mudar, pare.**
</item>

<item n="4" titulo="O resto da fase 17">
Na ordem das mensagens anteriores, com as condições de cada cartão:

1. o tick pelo projétil, com a sua própria subida de versão e a tabela antes → depois;
2. o histograma da força;
3. os `.rar`, conferindo a pasta `demos/entrada/_extraido/` antes de extrair e seguindo a regra 36.
</item>

<item n="5" titulo="A refatoração (cartão 9)">
Por último, antes da v2.

- **Cada módulo novo** fica sob a regra da pasta dele.
- **Se alguma regra de pasta precisar mudar de lugar,** mude junto e diga.
- **Proponha, sem implementar,** gerar a contagem de testes do `numeros_citaveis` automaticamente no build, pela coleta do pytest.
- **Nenhum número muda:** a impressão, as capturas e a catraca ficam idênticas.
</item>

<item n="6" titulo="A implementação da v2 (GOAT.demo)">
O design está fechado e aprovado pelo Pedro.

**A fonte é a especificação** `C:\Users\User\Desktop\TimeIA\Iriun\Sites\Base-Design\projetos\parser-cs2-v2.md`, com os arquivos em `C:\Users\User\Desktop\TimeIA\Iriun\Sites\Base-Design\prototipos\parser-cs2-v2\prototipo\`.

- A pasta do Iriun é **só leitura** para você: copie os arquivos para o repositório, nunca escreva lá.
- **Não traga** a pasta `fonte-agente/` nem a pasta `agentes/` (a TRV1). Elas têm material bruto e ficam fora do repositório.
- O `converte_agente.py` entra em `scripts/`, mas não roda no build. O manifesto dos agentes vem junto.

<v2_0 titulo="Plano: PARE aqui">
**Leia a especificação inteira e o protótipo.** Traga, numa mensagem só:

1. o plano em fases (a sugestão abaixo, ajustada ao que você encontrar);
2. a lista de arquivos que entram no repositório, com o destino de cada um;
3. **todas as dúvidas que forem escolha do Pedro,** com opções e a sua recomendação para cada uma;
4. o que conflita com uma regra do projeto e como você propõe resolver.

**Não comece a implementar antes da resposta.**
</v2_0>

<fases_sugeridas>
Cada fase é uma branch `v2-N-nome`. Merge quando:

- a suíte estiver verde;
- **a impressão dos números estiver idêntica.** A v2 muda só a forma, nunca um número;
- as capturas mudarem só onde a fase autoriza, com o antes e o depois no relatório.

1. **v2-1 · Base:**
   - os tokens novos e o validador de paleta passando nos temas A claro, A escuro e no mapa;
   - as fontes Geist e Geist Mono hospedadas no site, com a licença OFL e o fallback medido;
   - **o CSP passa a `font-src 'self'`,** e o `tests/test_csp.py` (linhas 70 e 71) muda junto. O Pedro autorizou essa mudança.
2. **v2-2 · Marca:**
   - a cabra C;
   - o wordmark GOAT.demo, com a mira no O a partir de 24 px;
   - o favicon;
   - os títulos das abas "GOAT.demo · Replay de CS2".
   - **O README vira "GOAT.demo · Replay de CS2"** (decisão do Pedro), e o endereço do site e o nome do repositório **não mudam**.
   - A seção de terceiros do README ganha:
     - os radares e os derivados (pontos e imagem de compartilhamento) vindos da Valve;
     - os agentes derivados de gravações do jogo;
     - tudo num projeto sem fins comerciais;
     - as fontes Geist sob a OFL.
   - **Nada da Valve entra na marca.**
3. **v2-3 · Navbar e landing:**
   - a navbar só com Partidas, Jogadores e Prancheta;
   - o topo com o título pixelado;
   - "Explorar partidas" como botão principal e "Adicionar demo" como secundário, com a linha "Em breve";
   - **o agente sorteado** (TR refinado ou CT-A, só o sorteado é baixado, o TR como padrão sem JavaScript, a mesma caixa, a linha de base `--ct`/`--tr`);
   - os mapas em pontos nas laterais a partir de 1440 px;
   - os números do `numeros_citaveis`.
4. **v2-4 · As páginas claras** (partida, jogadores e Perfil):
   - as pílulas com gooey só durante a troca de aba;
   - o `scroll-padding` da navbar;
   - os estados do Perfil (vazio honesto e com tipos validados), como na especificação.
5. **v2-5 · A prancheta** no tema escuro violeta.
6. **v2-6 · Os pontos e a imagem de compartilhamento:**
   - as máscaras de todos os mapas e a imagem de compartilhamento geradas no build;
   - a tela de carregamento com a máscara.
7. **v2-7 · A verificação final:**
   - o LCP e o CLS da landing e da partida;
   - os critérios A1 a A25;
   - as capturas de todas as páginas em 375 e 1440 px.

**Valem durante toda a v2:**

- **O comportamento não muda:** replay, prancheta, grupos e Perfil funcionam como hoje.
- **`GRUPOS_ATIVOS` continua `False`.**
- **O e-mail do Pedro nunca aparece no site.**
- **As pendências da especificação vão para o `notas/PENDENCIAS_PARA_O_PEDRO.md`:**
  - o teste do `Content-Encoding` dos dois `.js` dos agentes depois do primeiro deploy;
  - o fallback da fonte mono no macOS, sem métrica medida.
</fases_sugeridas>
</item>

<item n="7" titulo="Parte B dos grupos (Supabase): TRAVADA">
**Não comece até o Pedro escrever, nesta sessão, "Supabase pronto".** Quando ele escrever, termine o item em andamento, faça o merge e vá para a parte B, como combinado nas mensagens anteriores (B1 a B20, `npx supabase`, nunca a chave `sb_secret_` nem a do papel de serviço e nunca a senha do banco).

**Junto da parte B, responda as perguntas que o agente de segurança deixou abertas:**

1. **O plano:** o projeto Supabase está no plano Free, sem cartão (resposta do Pedro). Registre.
2. **A maior tática real:** meça o número de operações das maiores táticas que existem nos testes e nos exemplos da prancheta, e traga o máximo, a mediana e o p95. Isso confere se o teto de 5.000 operações por sala faz sentido.
3. **Segredos no histórico:** rode o `gitleaks` no histórico inteiro do repositório e traga o resultado. Se achar algo, **pare e não reescreva o histórico sem o Pedro.**
4. **Dependências:** rode o `npm audit` e o `pip-audit` e traga o que for alto ou crítico.
5. **O contato do aviso de privacidade:** use o link de Issues do repositório no GitHub, nunca um e-mail.
6. **Worktrees:** confira se `.claude/worktrees/` está no `.gitignore`. Se não estiver, coloque.

**Depois da parte B:** atualize o `grupos.md` de segurança com tudo isso, para o Pedro levar ao agente de segurança do Iriun. **`GRUPOS_ATIVOS` só vira `True` com o LIBERADO dele mais a confirmação do Pedro.**
</item>

---

<fora_desta_sessao>
**A investigação do awpy 3** (`PROMPT-investigar-migracao-awpy-v3-PARA-DEPOIS.md`) é numa sessão separada, na pasta `awpy-v3-teste`, só quando a calibração, os grupos e a fase 6 estiverem fechados. Não faça aqui.
</fora_desta_sessao>

<quando_parar>
- **A v2-0:** sempre.
- Uma dúvida que seja escolha do Pedro.
- Um número publicado mudar fora do que o item autoriza.
- O rating mudar.
- Qualquer `CLAUDE.md` passar do limite.
- O `gitleaks` achar um segredo.
- As paradas próprias de cada prompt citado.
</quando_parar>

<relatorio>
**Um relatório por parada, ou no fim, com:**

- os itens pulados por já estarem feitos;
- a tabela de cada item, feito ou parado, com o hash do merge;
- os tamanhos dos `CLAUDE.md`;
- o que ficou para o Pedro, também anotado no `PENDENCIAS_PARA_O_PEDRO.md`.

**Linguagem simples:** o Pedro lê pelo celular às vezes.
</relatorio>
