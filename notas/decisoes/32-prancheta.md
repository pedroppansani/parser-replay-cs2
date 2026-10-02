# Decisão 32: Prancheta tática: a tática é um LOG DE OPERAÇÕES, pronto para mais de um usuário

- **ID:** 32
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** A tática é um log de operações; desfazer é `anula`/`reativa`; interação por máquina de estados.

## Texto

32. **Prancheta tática: a tática é um LOG DE OPERAÇÕES, pronto para mais de um
    usuário** (Fase I, 2026-09-26). Página por mapa (`prancheta_<mapa>.html`
    no site; `dashboard/web/tactics.html` + `tactics.js`), mapa vazio, peças
    arrastáveis do banco, granadas com origem e destino, passos numerados.
    - **Estrutura multiusuário, sem servidor ainda** (`metrics/tactics.py`, com
      o PORQUÊ no cabeçalho): o arquivo guarda operações, não estado. Cada
      operação tem **id estável** (uuid), **autor**, **número de ordem** (`seq`,
      contador que só sobe -- relógio de Lamport) e data; o estado é aplicar o
      log na ordem (seq, autor, id), total e igual em qualquer máquina. Mesclar
      duas cópias é a UNIÃO dos logs por id: as duas pontas convergem (teste).
      Conflito (dois moveram a mesma peça no mesmo passo) vence o maior
      (seq, autor, id), e as duas operações ficam no log.
    - **Persistência atrás de interface**: a página só fala com `Armazem`
      (`lista`, `carrega`, `grava`, `apaga`). Hoje é o navegador
      (localStorage); um servidor entra implementando os mesmos métodos. A
      interface não supõe usuário único: campo de autor, índice com a lista de
      autores de cada tática, importar a MESMA tática mescla em vez de
      sobrescrever.
    - **Arquivo versionado**: `formato: "prancheta-cs2"`, `versao: 1`, com a
      impressão da calibração do radar (tática de outra calibração é recusada,
      mesmo motivo das anotações). O Python valida o arquivo exportado e há
      teste de que JS e Python chegam ao MESMO estado para o mesmo log.
    - **Prioridade: granada com arremesso REAL.** "Buscar arremesso" + clique
      onde a granada deve cair lista os arremessos do corpus que caem ali
      (raio ajustável na tela), e a granada escolhida carrega posição, ângulo,
      força/botão, postura, movimento e o comando `setpos`/`setang`
      (`grenade_throws.comando_de_console`, o mesmo do material de
      calibração). Arremesso correndo ou no ar sai com aviso (o comando não
      reproduz o movimento); o filtro "só parados" restringe a busca.
      Enquanto `COMANDO_CONFERIDO_NO_JOGO` for falso (decisão 21b), toda ficha
      avisa que o comando ainda não foi conferido no jogo. Arrastar a granada
      à mão desfaz o arremesso real (o comando deixaria de ser verdade).
    - A biblioteca (`data/lineups/<mapa>.json`, ~9 MB nos 8 mapas) é gerada
      LOCALMENTE por `py -3.12 -m scripts.build_lineups`, porque depende do
      interim, que não vai para o git nem para o CI. Só entra arremesso com
      reprodução exata. Regerar depois de mudar `metrics/grenade_throws.py`.
    - **Formato 2 (2026-09-26; a `versao: 1` acima é a do nascimento).** O
      leitor aceita 1 e 2; a 1 é MIGRADA EM MEMÓRIA -- nenhuma operação muda,
      só valem os padrões dos campos novos -- e exportar grava sempre a 2.
      `tests/fixtures/tatica_v1.json` foi exportada pela interface do código
      antigo (tag `baseline-antes-tatica`), e o teste de migração confere que o
      código novo dá o estado de `tatica_v1_estado.json` mais os padrões.
      Operações novas: `gira_peca`, `tira_peca`, `cria_traco`, `remove_traco`,
      `define_duracao`, `define_vida`, `anula`, `reativa`; `nivel` (andar) nas
      de peça e granada. O estado guarda `posicoes` como `[x, y]` e o andar em
      `niveis` separado (um teste existente exige `[x, y]`, e assim a migração é
      só acréscimo). `problemas(doc)` devolve TODOS os defeitos, e `valida`
      mantém a assinatura e leva todos na mensagem.
    - **Desfazer é `anula`/`reativa`, o mecanismo ÚNICO de desfazer e
      refazer.** Mira operação do MESMO autor, nunca outra anula/reativa; vale a
      última sobre cada alvo, na ordem do log. Nada sai do log, então a mescla
      por união continua convergindo (há teste com dois autores desfazendo em
      paralelo), e um mecanismo só serve para toda operação: anular um
      `remove_peca` devolve a peça com o histórico, anular um `move_granada`
      devolve o arremesso real. Não crie operações inversas por tipo.
    - **Vida útil em `dura_passos` (null = até o fim), contando PASSOS.** Um
      elemento criado no passo de índice p aparece em i se p <= i < p + dura.
      Não guarda o id do passo final porque remover um passo no meio deixaria a
      referência apontando para o nada; contando passos, a conta continua certa
      (há teste). Padrões, convenção de interface: smoke até o fim; flash, HE,
      molotov, decoy e traço, 1 passo.
    - **Ordem de criação = o `(seq, autor, id)` da operação `cria_*`**, sem
      contador próprio: o log já tem a ordem total, e um segundo contador
      divergiria na primeira mescla. É ela que a reprodução usa para riscar os
      desenhos na ordem em que foram feitos.
    - **"Tática deste instante"** (2026-09-26/27, decisões do Pedro): o botão na
      barra do mapa do replay abre a prancheta do mesmo mapa com uma tática
      nova montada do QUADRO i0 = floor(pos) -- o mesmo que o `draw()` usa para
      `alive`; a dica diz que é a amostra gravada imediatamente anterior (4 por
      segundo), e o relógio do título é o desse quadro (`relogioDe`), não o da
      tela.
      - **Só vivos viram peça**, com posição, direção (`d`) e andar (`lv`) da
        amostra, sem interpolar, e o NOME do jogador como rótulo. **Mortos não
        viram peça** (morto no mapa é ruído editável): vão no PLACAR DE VIVOS do
        título ("match_05 · round 9 · 1:12 · 4v3", sempre TR antes de CT) e na
        descrição da tática, por lado e na ordem das mortes (a ordem é o
        primeiro quadro em que o jogador aparece morto no `alive`).
      - **O retrato viaja na URL** (`#instante=`), que funciona igual em
        arquivo local e no site, e é CONSUMIDO com `replaceState`: recarregar
        ou voltar no navegador não cria segunda tática (teste). Cada jogador e
        cada granada são conferidos antes de entrar; o que não fecha fica de
        fora com aviso.
      - **Metadado `origem`** no documento ({partida, round, quadro, relogio,
        elenco, mortos}): da criação, imutável como `mapa` e `calibracao`, não é
        operação; validado em `problemas_da_origem` e no espelho JS. Com ele o
        **banco mostra os jogadores reais do round** (vivos e mortos) em vez de
        "TR 1..5": arrastar um nome move a peça dele se ela existe, e cria a
        peça com o nome se não existe (o morto, para planejar "e se"). O banco
        consulta o metadado, nunca infere dos rótulos.
      - **Granadas ativas no instante** entram no passo 1, ligadas ao arremesso
        REAL que as gerou -- nunca por proximidade. O `export_replay` grava em
        cada smoke, fogo e granada em voo o campo `l` = {id da biblioteca,
        posição de soltura}: smoke e voo pelo `entity_id` do PROJÉTIL (a smoke
        É o projétil: mesma entidade em 100% das 7.423 do corpus); fogo pelo
        TICK -- o incêndio é outra entidade, mas o projétil do mesmo
        arremessador termina exatamente 1 tick antes do fogo em 98,2% dos 5.678
        incêndios (`TICKS_DO_PROJETIL_AO_FOGO`). Com o id na biblioteca, a
        granada entra com o arremesso real e o comando; sem ela, com origem na
        soltura; sem ligação, com `origem_desconhecida`. Smoke fica até o fim,
        molotov 1 passo; granada no ar usa o fim da trajetória como destino;
        flash e HE já estouradas não entram. No corpus: 36.891 de 37.002
        ligadas, 111 sem ligação (103 fogos, 8 em voo).
    - **`origem_desconhecida`** (opcional em `cria_granada`): a granada de um
      instante cujo efeito não se liga a arremesso nenhum. `origem == destino`
      sozinho seria um valor falso (linha de comprimento zero, e passaria por
      arremesso de verdade na validação); com a flag, `problemas()` EXIGE
      origem igual ao destino e RECUSA a flag junto de arremesso real, o
      desenho mostra só o efeito, e o campo só existe no estado quando é
      verdade (sai no `move_granada`, quando a pessoa dá uma origem).
    - **Prancheta fluida (2026-09-27): a interação é UMA máquina de estados**
      (`ESTADOS` e `estadoDaInteracao` em `tactics.js`): livre,
      peca_selecionada, colocando_peca, granada_origem, granada_destino,
      granada_selecionada, desenhando e buscando. Cada clique faz uma coisa
      previsível, e a linha de dica (`#pr-dica-estado`) diz qual é ANTES do
      clique. Clique x arrasto por `LIMIAR_ARRASTO_PX` (4 px de tela): o clique
      é um caminho a mais, o arrasto continua como era. Nenhuma operação nova:
      mover por clique é move_peca, botão direito é gira_peca (a peça olha para
      o ponto), granada é cria_granada. Granada a partir da seleção: 1-4 e um
      clique criam a granada saindo da peça, que continua selecionada; com
      biblioteca, a lista de arremessos reais abre em seguida e a primeira
      opção é manter a desenhada (escolher um real troca: remove_granada +
      cria_granada). Texto no próprio mapa (sem window.prompt). Atalhos num
      mapa único `ATALHOS`, sem tecla repetida (teste), com o painel "?"
      gerado dele. Dois desvios do pedido, forçados pelos testes existentes
      (que passam sem alteração): os botões Selecionar / Buscar arremesso /
      Desenhar à mão continuam numa linha do painel (os testes os clicam em
      `aside`), e clicar na peça JÁ selecionada não a desmarca (um teste marca
      a peça e clica nela esperando que siga selecionada) -- desmarcar é o
      Esc. Métrica de fluidez (roteiro fixo: 5 CT, 2 smokes de jogadores
      diferentes, mover 2 no passo 2): 15 ações antes, 14 depois.
