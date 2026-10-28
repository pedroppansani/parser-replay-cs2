# Prompt: respostas ao plano da v2 (v2-0), aos pisos e aos exemplos de flash

Cole na sessão do Claude Code do projeto, tudo a partir da linha `---`.

---

<veredito>
**O plano da v2 está aprovado.** O `PLANO-v2-0.md` ficou muito bom, e as 14 inconsistências da especificação apontadas foram exatamente o que eu precisava saber.

Respostas abaixo. **Pode começar a v2-1** depois de fechar os itens de calibração desta mensagem.
</veredito>

---

<calibracao>

<r tema="Flash no time: os 3 exemplos novos">
**O Pedro respondeu "sim" no #1 (molodoy), no #4 (kyxsan) e no #10 (910).**

- O tipo fecha 10/10 e entra em `TIPOS_DE_ERRO_VALIDADOS`.
- Grave as respostas em `scripts/calibracao/respostas_do_pedro.json`, com a data.
- Atualize o material e a nota 46.
- O Perfil publicado passa a mostrar a flash no time, e isso está autorizado: traga a captura antes e depois de um jogador que tenha o ponto.
</r>

<r tema="Os pisos (item 1 da calibração)">
**O piso de suporte é 40,** pela regra que o Pedro já tinha dado: testar 30 e, se as estrelas continuassem acima, usar 40.

- Se, mesmo com 40, um AWPer ou o donk ficar acima do corte, siga assim:
  - para o AWPer, a prioridade de exibição mostra "AWPer" na tela;
  - o rótulo de suporte do donk em alguma partida é aceito, como o Pedro aceitou para o ZywOo.
- Traga a fronteira de 40 no relatório, só como registro.

**A outra pergunta, sobre a `jogadores.html`:** o Pedro não viu o texto dela.

- **Se for técnica** (como mostrar, onde colocar, captura), decida você e explique no relatório.
- **Se for escolha de jogo ou de texto do site,** refaça a pergunta no próximo relatório, curta, com opções e a sua recomendação.
</r>
</calibracao>

---

<v2_respostas>

<duvidas tema="As 10 dúvidas da seção 3: o Pedro aceitou todas as recomendações">
1. **GitHub:**
   - um link discreto no rodapé da landing;
   - o link de Issues dentro do diálogo "Adicionar demo".
2. **O botão principal:**
   - "Explorar partidas" leva à lista;
   - a partida de exemplo (o mesmo critério declarado de hoje) vira o primeiro card, em destaque.
3. **A comparação do Perfil:** só a forma nova, sobre o comportamento de hoje.
   - A comparação por grupos com "quem está à frente" vira uma fase própria depois da v2, com a regra de empate definida pelo Pedro.
   - Anote em `PENDENCIAS_PARA_O_PEDRO.md`.
4. **O mini-radar fica fora da v2.** Se um dia entrar, o nome é "mini-mapa".
5. **O carregamento:** um esqueleto com a máscara do mapa, sem porcentagem. Ele serve também contra o CLS.
6. **Os comandos de console** (`setpos`/`setang`) continuam em `--f-codigo` (mono do sistema). O resto do código segue a especificação.
7. **A imagem de compartilhamento é uma por partida,** com o placar.
8. **e 9. Os textos da especificação estão aceitos** (estado vazio do Perfil e diálogo "Adicionar demo"), com o link de Issues e sem e-mail.
10. **O agente sorteado fica na landing,** com a linha de terceiros no rodapé. Confirmado.
</duvidas>

<testes tema="A seção 4.4">
**O Pedro autorizou ajustar os testes de visual da lista da seção 4.4,** nestas condições:

- antes de mudar um teste, tente manter os ids e as classes para não precisar mudá-lo, como você propôs;
- **só os testes de visual** (tokens, favicon, títulos, landing, cabeçalho, `og:image`, paleta, seletores);
- **nunca** um teste de número, rating, dado, catraca, impressão dos números ou cálculo de métrica;
- cada teste mudado vai ao relatório da fase com o diff e o motivo;
- **se aparecer um teste fora da lista** que precise mudar, pare e traga.
</testes>

<conflitos tema="As suas resoluções da seção 4 estão aprovadas">
- **4.1:** só as linhas 70 e 71 do `test_csp.py`, e um teste novo de `file://`.
  - Se o `agente-*.js` não carregar em `file://` com `script-src 'self'`, **não afrouxe o CSP.** O quadro fixo em SVG já basta para quem abre o arquivo solto; o site real é HTTP.
  - Diga o resultado.
- **4.3:** os tokens `tinta-mapa`, `foco-mapa`, `tinta-2-mapa`, `apagado-mapa` e `fundo-mapa`, com os valores escuros de hoje, validados contra o `--radar`.
  - A troca nos testes de granada e da peça (para `*-mapa`) está autorizada.
  - O mapa continua escuro nos dois temas.
- **4.5 e 4.6:** os pontos e a imagem de compartilhamento gerados com Pillow, lendo o radar do JSON, sem navegador no build, com as fontes estáticas da Geist versionadas.
- **4.7:**
  - a nota 48 nova (vigente), e a 44 continua vigente com o aviso "revista pela 48";
  - as regras de build da v2 vão para a nota 48 e para o `dashboard/web/CLAUDE.md`;
  - **o `scripts/CLAUDE.md` não ganha linha.** Se uma regra precisar estar nele, pare e traga a proposta de divisão.
- **4.8:** os critérios recalculados como na sua tabela, e rode o `mede_radar` e o `mede_granada_real` também, já que o tamanho do canvas mudou.
- **4.9:** as referências do `compara_capturas` regeradas em commit próprio, com a lista do que mudou. Se uma peça ou o fundo mudar de pixel, é bug.
- **4.10:** o extrator da impressão pode mudar para acompanhar as classes novas, desde que **produza as mesmas linhas.** Mostre a comparação dos dois extratores.
- **4.12:** o `v2.css` injetado pelo `design_head`, e os textos saindo de Python.
</conflitos>

<inconsistencias tema="Seção 6">
Siga as suas resoluções:

- os agentes em `dashboard/web/agente/` no repositório e em `docs/agente/` no site;
- o sha256 do manifesto vale, e não o tamanho;
- **sem JavaScript, aparece o quadro fixo do TR,** que é o padrão;
- os tokens que a especificação não lista são recalculados na v2-1;
- os cortes de privacidade por agente: 545 no CT e 590 no TR.

O `preload` das fontes (item 12 da seção 6) é medido na v2-7, no Pages.
</inconsistencias>

<ordem_v2>
1. **v2-1:** a base. Não muda a aparência; o tema escuro atual passa a ser `data-tema="escuro"`.
2. **v2-2:** a marca.
3. **v2-3 e v2-4 em sequência, numa branch de integração, e para a `main` no mesmo push,** para o site nunca ficar meio claro e meio escuro. Antes desse push:
   - as capturas de todas as páginas, em 375 e 1440 px;
   - a impressão dos números idêntica.
4. **v2-5 e v2-6:** podem ir em paralelo, depois de a v2-4 ter mesclado o `map_core.js`.
5. **v2-7:** a verificação final.

Merge e push de cada fase sem esperar confirmação, quando:

- a suíte estiver verde;
- a impressão dos números estiver idêntica;
- só tiverem mudado as capturas e os testes autorizados.

Com o merge da v2-7, ponha no `PENDENCIAS_PARA_O_PEDRO.md`:

- o `curl` do `Content-Encoding` dos dois agentes depois do deploy;
- o fallback da fonte mono no macOS.
</ordem_v2>
</v2_respostas>

<lembretes>
- **A fila do prompt mestre continua:**
  - o `fix-tickrate-resto` (que está com um agente) termina e entra antes da v2-1;
  - o resto da fase 17 e a refatoração seguem a ordem do mestre.

  Se a refatoração ainda não foi feita, **faça-a antes da v2-1:** ela mexe na estrutura e a v2 mexe na forma, e juntas elas brigam.
- **`GRUPOS_ATIVOS=False`** em toda a v2. A parte B continua travada até o Pedro escrever "Supabase pronto".
- Atualize o `notas/estado-atual.md` depois de cada merge.
</lembretes>
