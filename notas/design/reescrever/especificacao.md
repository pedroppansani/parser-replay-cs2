# Parser de Replay CS2 · "Reescrever" (GOAT.demo) · documento de entrega para o Pedro escolher

> **Para quem:** o Pedro (escolha) e, depois do OK, a sessão do projeto (implementação). **Data:** 2026-11-04.
> **Estado:** PROPOSTA. Nada foi implementado; o design não mexeu no projeto (só Read/Glob/Grep lá). As decisões abertas estão na §12.
> **Protótipo navegável** (abre como arquivo): `prototipos/parser-cs2-reescrever/prototipo/index.html` (índice). Páginas: `partida.html?estado=assistir|instante|editando|tocando|granada|granada-carregando|granada-erro` (com `&moldura=a|b`, `&tema=claro|escuro`, `&vista=real|versao`), `escolha.html`, `landing.html` (`?nome=ese`), `pecas.html`.
> **Capturas:** `prototipos/parser-cs2-reescrever/capturas/` (375×812, 1366×768, 1440×900; `comparacao-temas-1440.png`, `navbar-reescrever-x-ese.png`). **Medidas:** `validacao/saida-medidas.txt`.
> **Gerador:** `gera_reescrever.py` (HTML a partir do dado), `prepara_dados.py` (recorte do radar e alternativas, a partir do site no ar).
> **Dados dos exemplos:** reais, do site publicado (2026-11-04): match_43, FURIA 13 × 11 Vitality, Mirage, IEM Krakw 2026, round 23 (o decisivo). A única coisa desenhada à mão é a edição do usuário (o caminho novo do ZywOo), que é o que o usuário faria.

---

## 1. As duas recomendações

**1.1 Onde mora: dentro da partida, como um modo da aba Replay** (não uma página própria).
- Três das quatro portas já estão dentro da partida: o botão do Replay, o botão do erro (bloco "Por que … perdeu este round", na mesma aba) e os chips do Perfil. A quarta (navbar) leva à página de escolha, que abre a partida já no modo.
- A página da partida já tem o round carregado (2,4 a 5,2 MB por partida, medido em 4 páginas): uma página própria baixaria tudo de novo.
- Reaproveita o modo palco (decisão 53) inteiro: a faixa de rounds, o mapa de um tamanho só e a rolagem até o palco.
- Endereço: `match_43.html#replay&r=23&reescrever=0:55&sel=ZywOo` (formato a fechar na implementação; serve também ao "compartilhar por link" de depois).

**1.2 O tema: variação B, o violeta da prancheta.** Ao entrar no Reescrever, o palco e as duas colunas viram a ilha `data-tema="violeta"`; o mapa continua `--radar`, o entorno do canvas fica `--fundo` violeta. Motivo: no site o violeta já quer dizer "prancheta = plano" (decisão 51: violeta nos dois temas), então a cor carrega a regra de honestidade sem token novo; real = a moldura do Replay, plano = violeta. A variação A (moldura do Replay, só o "▶ Sua versão" quente) muda pouco na página escura: em `tema-escuro-moldura-a-1440.png` o Reescrever é quase igual ao Assistir. Nada depende só da cor: a pílula "● Reescrever", "Sair", a frase fixa e os rótulos "Real" / "Sua versão" dizem o modo em texto.

## 2. Tokens

**Nenhum token de cor novo.** Usa os do `dashboard/web/tokens.css` (cópia em `prototipo/css/tokens.css`, lida em 2026-11-04).

| Uso | Token | Observação |
|---|---|---|
| Moldura e colunas no Reescrever (B) | bloco `violeta` inteiro | o mesmo da prancheta |
| "▶ Sua versão" | `--quente-1` → `--quente-2`, texto `--quente-ink` | mesmo papel do "Reproduzir" da prancheta, uma vez por tela. **Só na variação A** o degradê precisaria existir também no bloco `escuro` (no protótipo, 3 linhas no fim do bloco escuro); na B não muda nada |
| Peças, fantasma, losango, caminho | `--tinta-mapa`, `--contorno`, `--ct-mapa`, `--tr-mapa`, `--apagado-mapa`, `--tinta-2-mapa`, `--smoke`, `--molotov` | os do canvas, iguais em todo tema |
| Real antes do instante, na linha do tempo | hachura de `--tinta-2` | forma (hachura) e a palavra "real" |

## 3. A peça em todos os estados (cartão 22) · `pecas.html`

Regra: **real × sua versão é FORMA (cheio × vazado tracejado), nunca alfa nem cor** (Capacidades 2026-10-13: alfa de 85% dá ΔE 0,2 a 0,6). Todas com o anel duplo (contorno `#05080b` + halo `#e8edf2`).

| Estado | Desenho | Onde |
|---|---|---|
| Real (Assistir) | disco cheio na cor do lado + gota da direção | Replay, como hoje |
| Sua versão, editável | o mesmo, 25% maior; alvo de toque de 44 px; selecionado = anel branco 2 px sobre contorno 4 px | editando |
| Sua versão, tocando | igual ao real (é a protagonista) | tocando |
| Fantasma (real onde difere) | anel vazado tracejado 5/4 (o `estado: "fantasma"` que já existe no `map_core.js`), sem nome; linha pontilhada `--tinta-2-mapa` até a peça da mesma pessoa na sua versão | tocando, só do que difere |
| Morto | ✕ com halo e contorno; traço do lado a 60% (como hoje) | todos |
| Morte do real (fantasma) | ✕ vazado: só halo e contorno, sem a cor do lado | tocando |
| Outro andar (real e sua versão) | disco cinza `--apagado-mapa` + anel interno do lado + ▲/▼ + nome em itálico (o do Replay de hoje, decisão 52) | Replay e Reescrever |
| Outro andar, editável | o mesmo, 25% maior e editável. **Sai o esmaecido (`ALFA_OUTRO_ANDAR`) da prancheta** | Reescrever e, se o Pedro quiser, a prancheta |
| Outro andar, fantasma | anel cinza tracejado + anel interno do lado tracejado + seta | tocando |

Só desenha fantasma **onde a sua versão difere do real**: quem não foi editado anda igual nos dois, e 10 fantasmas em cima de 10 peças só poluiriam. A legenda diz "real, onde difere".

**Contraste medido** (`validacao/saida-medidas.txt`, recorte inteiro do radar da Mirage, 10.453 cores): anel duplo, pior pixel **4,13:1** (meta 3:1; só o halo daria 2,64:1 e só o contorno 1,01:1); disco CT contra o contorno 6,16:1, TR 8,99:1, cinza do outro andar 6,76:1. Vale para sua versão, fantasma e morto (o tracejado usa os mesmos anéis). Mapas com radar mais claro: refazer com o `mede.py` por mapa (a tabela `RADAR_AJUSTE` já foi feita para isso).

## 4. Telas e estados (ordem do HTML = ordem do celular)

### 4.1 Assistir (Replay de hoje) · `partida.html?estado=assistir`
- **"Abrir round na prancheta" vira "Reescrever este round"** (decisão do Pedro) e **sobe para o cabeçalho do palco**, como botão principal. Motivo medido: no modo palco a barra de botões fica abaixo da dobra (1440×900 e 1366×768); o botão continua também na barra, com o mesmo nome.
- Abre no instante em que o Replay está parado (o mesmo `instante()` de hoje).

### 4.2 Escolher o instante · `estado=instante`
- O round real continua tocando e sendo arrastado normalmente. No transporte, ao lado do ▶: **"Reescrever daqui · 0:55"** (o relógio do quadro inteiro `floor(pos)`, como o `instante()`); no celular, só "Reescrever daqui".
- Acima do trilho: "pare aqui e toque em Reescrever daqui".
- Coluna da direita: a frase fixa e a dica. Coluna da esquerda: o banco das 10 peças (CT e TR juntos).

### 4.3 Editando · `estado=editando`
- As 10 peças nas posições reais do instante, editáveis (as regras da prancheta: decisões 35, 42 e 43, "editar em t corta o real dele depois de t e ancora o estado real em t"; mover anda na velocidade medida).
- **Linha do tempo:** antes do instante, hachura + "real"; no instante, o **losango** (o mesmo glifo do mapa) + "**sua versão** desde 0:55"; depois, o trilho cheio.
- **No mapa:** losango no ponto de cada jogador editado no instante ("aqui a sua versão começa"); caminho novo branco sobre contorno; pílula "chega 0:51".
- **Quem já morreu antes do instante** fica onde morreu, ✕ do real, **não editável**; no banco, "morto às 0:56, antes de 0:55" (exemplo real: yuurih e flameZ).
- **Banco** (coluna da esquerda no computador; embaixo do painel no celular): nome, vida, arma e lugar do dado; o editado ganha a pílula "editado". Clicar seleciona.
- **Painel** (coluna da direita): título, frase fixa, "Sua versão começa em 0:55", dica (`role=status`, sem limite de linhas porque a coluna não empurra o mapa), ferramenta Mover | Granada (radiogroup), "Levar o ZywOo até" (lista dos lugares do dado: o caminho pelo teclado), Desfazer / Refazer, Voltar ao real, Fantasma do real (interruptor com o estado escrito), "O que mudou" (texto), "Depois" (os três lugares reservados).
- **Sair** fica no cabeçalho do palco (sempre à vista no modo palco).

### 4.4 Tocando com o fantasma · `estado=tocando`
- "▶ Sua versão" toca a sua versão; o real passa por baixo **só onde difere** (§3).
- **Onde se separam:** o losango no ponto de partida + a linha pontilhada entre o fantasma e a peça da versão (cresce enquanto eles se afastam).
- Granada do real que **depende de quem foi editado** (lançada por ele depois do instante) fica **só no fantasma** (exemplo real: a smoke do ZywOo das 0:54 em JUNGLE). Granadas de quem não foi editado acontecem nos dois.
- Botão do fantasma: o interruptor do painel (`Fantasma do real: Ligado/Desligado`).

### 4.5 Trocar a granada · `estado=granada` (sessão de exemplo em 1:55)
1. **Escolher a granada real:** com a ferramenta Granada, clicar numa granada do real lançada **depois** do instante (no celular, pela lista "Granadas do round"); a origem ganha o anel tracejado branco.
2. **A lista** (painel; no celular embaixo do mapa, sem sobrepor): "Granada do real: smoke do ropz às 1:54, de T SPAWN para CATWALK" e as alternativas **lançadas de verdade**: mesmo tipo, a até 150 u de onde ele estava, **agrupadas pelo lugar do destino** (o nome do dado), o grupo com mais arremessos primeiro; em cada grupo, o mais perto da origem. Linha 1: destino + quantos; linha 2: quem, evento, round, distância; linha 3: postura, movimento, pulando/no chão, "lido da demo"/"inferido" (a fonte que a biblioteca já declara, decisão 21a). O grupo do destino original leva "o mesmo do real". Exemplo real: SNIPERS NEST 107 (KSCERATO, PGL Cluj Napoca 2026, R23, a 2 u), CATWALK 34, UNDERPASS 2, T RAMP 1, MIDDLE 1 (`dados/alternativas.json`).
3. **No mapa:** o voo e a smoke originais em fantasma (tracejados); a escolhida com o voo pontilhado e a smoke cheia, **no destino real em que caiu**.
4. Uma linha de fato quando houver: "No real, o mezii já joga uma smoke em SNIPERS NEST às 1:54".
5. "Trocar" / "Cancelar". Se a origem estiver longe, vale o aviso de atraso da prancheta (`chegadaPossivel`, "+N s", oferecer adiar).
- **Carregando** (`granada-carregando`): "Carregando os arremessos reais da Mirage (6.701 arremessos de 16 partidas)…" (`role=status`) + esqueleto de 3 linhas com a altura da lista. Sem porcentagem: o `<script>` não informa progresso.
- **Erro** (`granada-erro`): "✕ Erro: os arremessos reais não carregaram. A troca de granada fica desligada; o resto do Reescrever continua." + "Tentar de novo" (`role=alert`, `--erro`). É falha do sistema, por isso a cor de erro.

### 4.6 Reescrever o erro · o bloco "Por que Vitality perdeu este round"
- Cada momento com jogador ganha à direita um botão quieto **"Reescrever"** (borda `--borda`, 44 px). O `aria-label` diz o resto: "Reescrever a partir de 0:55 no relógio, 3 s antes, com ZywOo selecionado". O tempo não vai no botão porque o bloco mostra o tempo decorrido (0:12, 1:02) e o resto do Replay mostra o relógio; pôr um do lado do outro confunde.
- Abre direto em **editando**, 3 s antes (a mesma folga dos chips do Perfil), com o jogador selecionado. Momento sem jogador (`sem_plant`) não ganha botão. Na virada numérica, o selecionado é a vítima.
- A frase do fim do bloco ganha: "…ou em **Reescrever** para mudar a jogada a partir de 3 s antes."
- No celular o botão desce para baixo do texto, alinhado ao texto.

### 4.7 Celular (375 px)
- Sem fantasma por cima: no tocando, embaixo do transporte, **[Real | Sua versão]** (radiogroup de 44 px); o mapa mostra um ou outro e o relógio do mapa diz qual ("Real · 0:51"). O interruptor do fantasma some no celular.
- Edição como a da prancheta no celular: tocar e mover a peça, granada pela lista, sem desenho à mão. A lista "Levar até" ajuda quem não arrasta.
- A frase fixa vai na legenda, logo embaixo do transporte (no computador, no topo do painel).

### 4.8 Página de escolha · `escolha.html` (o link "Reescrever" da navbar)
- Título "Reescrever um round", uma frase do que é, a frase fixa.
- **Sugeridos:** uma linha por round (não três cartões iguais): mapa · evento, times e placar, round; à direita, os motivos escritos: ◆ `--decisivo` "Decidiu a partida · levou o FURIA de 50% para 75%…" (a frase do `narrative.decisive`) e □ "ZywOo · morreu sozinho · 0:52 · erro validado, depende da tática" (borda cheia = explícito, tracejada = depende, a gramática da §19); botão "Reescrever o round 23". Decisivo abre no **instante** (1:55); erro abre em **editando** 3 s antes, com o jogador.
- **Buscar:** campo "Partida: time, mapa ou evento" → lista que filtra (`role=status` com a contagem) → a partida escolhida abre a faixa de rounds → "Reescrever o round N". Vazio: "Nenhuma partida com 'xyz'." + "Limpar a busca".

### 4.9 Navbar e landing · `landing.html`
- Navbar: **Partidas · Jogadores · Reescrever**; comparação com "E se…?" em `navbar-reescrever-x-ese.png` (cabe nos dois tamanhos). A Prancheta sai da navbar.
- Bloco **"Monte uma tática do zero"** depois da lista de partidas: frase, chips dos 8 mapas, "Abrir a prancheta da Mirage" (muda com o chip), "O endereço de sempre continua valendo: prancheta_de_mirage.html", e à direita a miniatura no violeta (a prancheta é violeta).

## 5. Textos fixos (do Python, decisão 18)
- Frase fixa: "**Não é uma previsão.** A sua versão é um plano desenhado sobre o round real: o site não simula o CS2 e não diz quem venceria os duelos." Curta, no cabeçalho: "**Real** e **Sua versão** · plano, não previsão".
- Rótulos: "Real", "Sua versão", "Reescrever este round", "Reescrever daqui", "▶ Sua versão", "Sair", "Voltar ao real", "Fantasma do real", "O que mudou", "Levar o <nick> até", "chega <relógio>", "morto às <relógio>, antes de <relógio>", "real, onde difere", "onde a sua versão começa", "morte do real".
- **Nunca** na sua versão: placar, porcentagem, "venceria", "ganhou", ícone de vitória, cor de vencedor.

## 6. Acessibilidade
- **Teclado:** o banco é a lista de peças (botões com `aria-pressed`); "Levar até" move pela lista de lugares do dado; o trilho é `role=slider` com `aria-valuetext` "0:55, sua versão desde 0:55"; Mover/Granada e Real/Sua versão são `radiogroup`; atalhos do Replay continuam (espaço, setas). O foco nunca fica atrás das barras grudadas (decisão 53).
- **Leitor de tela:** "O que mudou" é o texto da diferença ("ZywOo sai do CONNECTOR às 0:55 e vai até T RAMP pelo STAIRS. No real, morreu para molodoy às 0:52."; "A smoke do ZywOo das 0:54 (JUNGLE) fica só no real…"); a dica é `role=status`; o mapa tem `aria-describedby` com quem está vivo e morto.
- **Reduzir movimento:** `--dur` 0 ms (medido); rolagem até o palco instantânea; a reprodução só começa com o clique.
- **Medido** (`saida-medidas.txt`, 15 páginas/estados × 3 tamanhos): rolagem lateral 0; textos abaixo de AA 0 (cerca de 160 a 210 por página, fundo composto); alvos abaixo de 44 px 0.

## 7. CLS e o mapa de um tamanho só
- O mapa tem o mesmo [x, y, lado] em **todos os estados** (medido: 325 px a 375, 447 px a 1366×768, 579 px a 1440×900), porque nada que muda fica acima ou ao lado dele com tamanho variável: o cabeçalho (55 px) e o transporte (57 px) têm a mesma altura em todo estado; os botões da esquerda do transporte moram numa caixa de largura fixa (244 px; 136 px no celular), então o trilho não muda de largura; as colunas têm `contain: size` (não crescem com o conteúdo, rolam dentro).
- Medido: **CLS 0,0000** na carga e no percurso por cliques (Reescrever este round → daqui → tocar → pausar → granada → trocar → sair), nos três tamanhos. No teste duro (trocar de estado por script, sem clique) sobram 0,0097 (1366) e 0,0179 (1440), todos de conteúdo do painel da direita que muda de lugar dentro da coluna; o navegador não conta isso quando vem de clique, e o mapa não se move. Se o Pedro quiser zero também aí, o painel ganha uma ordem fixa por estado (custa linhas vazias).

## 8. O que o dado sustenta e o que falta

Conferido no export do Replay (`scripts/export_replay.py`) e no payload das páginas publicadas:

| Ideia | Dado | Situação |
|---|---|---|
| Posição, ângulo de visão (yaw), vivo/morto, vida, arma na mão, lugar, andar | por quadro, 4 por segundo (`x`, `y`, `d`, `alive`, `hp`, `w`, `p`, `lv`) | **sustenta** |
| Mortes (quem, por quem, arma, posição dos dois), plant, desarme | `events` com horário fracionário | **sustenta** |
| Granadas: voo, efeito, quem lançou, ligação ao arremesso real | `nades`, `smokes`, `fires`, `pops`, `blinds`, `l.id` | **sustenta** |
| Biblioteca: origem, destino, força, botão, postura, movimento, no ar, fonte lido/inferido | `arremessos/<mapa>.js` | **sustenta** |
| "Mesmo lado" nas alternativas | a biblioteca **não tem o lado** | **falta**: gravar o lado no build (`partida` + `round` + `jogador` já estão na entrada). No protótipo, todas as 146 saem de T SPAWN, o que não prova o lado |
| Tempo de voo e de efeito da alternativa | a biblioteca não tem `voo_s`/`efeito_s` (o round real tem) | **falta** para a granada trocada cair no instante certo; levar do export, como a decisão 43 fez com as do round |
| Granadas no inventário por instante | não exportado (só a arma na mão); o inventário só existe no fim do freeze (`compra.parquet`) | **falta**. A v1 não precisa (só troca granada que foi lançada), mas "jogar uma granada que ele não jogou" precisaria |
| Dinheiro por instante | `balance` está no `ticks.parquet`, não no Replay | **falta no site**; não é usado na v1 |
| Pitch (para cima/baixo) | não exportado | não é usado |
| Quem venceria um duelo, o placar da sua versão | não existe simulação | **nunca**: é a regra de honestidade |
| "Quando fizeram isso de verdade" | não há índice de situações parecidas | **falta** (fase própria): definir "parecido" (posição, instante, lado) e mostrar n e a amostra |
| Erro do round com jogador e instante | o bloco do Replay tem `moments` com `who` e `tick`; o Perfil tem `chips` por tipo validado com `round` e `t` | **sustenta** (ver §12, D5: as duas listas são diferentes) |
| Sugeridos da página de escolha | `decisive_round` + `narrative` + `chips` do Perfil, por partida | **sustenta**, mas o build precisa juntar num índice pequeno (as páginas têm de 2,4 a 5,2 MB) |

## 9. Regras de comportamento para a implementação (confirmar)
- Tudo que não foi editado toca como no real, **inclusive as mortes**. Morte cujo matador foi editado: ver D3.
- Granada lançada **depois do instante** por quem foi editado sai da sua versão (fica no fantasma), porque dependia da posição real dele.
- Quem morreu antes do instante não é editável.
- Nada é editável enquanto a sua versão toca (decisão 35).

## 10. Lugar reservado para depois (sem funcionar na v1)
No painel, bloco "Depois" tracejado: "Quando fizeram isso de verdade", "Compartilhar por link", "Salvar no grupo", cada um com `tag neutro` "em breve". Quando entrarem, ocupam esse mesmo espaço (a coluna rola por dentro; o mapa não muda).

## 11. O que muda no projeto (só depois do OK)
- `template.html`/`partida/02-replay.js`: o botão renomeado e no cabeçalho do palco; o modo; o painel e o banco nas colunas; o botão em cada momento do bloco de erros.
- `map_core.js`: o estado "fantasma-morto" e o "fantasma-outro"; o editável do outro andar (sai o `ALFA_OUTRO_ANDAR` da prancheta se o Pedro aceitar D4).
- `prancheta/*`: o modelo de edição em t (decisão 43) chamado de dentro da partida, sem a página da prancheta.
- Build: índice dos sugeridos; o lado e o `voo_s`/`efeito_s` na biblioteca; a página `reescrever.html`; o bloco na landing; a navbar.

## 12. Decisões abertas para o Pedro
- **D1 · Onde mora:** (a) modo da aba Replay; (b) página própria. **Recomendo (a)** (§1.1).
- **D2 · Tema:** (A) moldura do Replay + só o "▶ Sua versão" quente; (B) violeta da prancheta. **Recomendo B** (§1.2). Ver `capturas/comparacao-temas-1440.png`.
- **D3 · Morte cujo matador você mudou:** (a) acontece como no real e "O que mudou" avisa ("No real, X morreu para Y; Y saiu do real na sua versão"); (b) o usuário escolhe manter ou tirar (tirar = a peça para no ponto, porque não há dado depois da morte). **Recomendo (a)**: é o mais honesto e não inventa.
- **D4 · Peça do outro andar na prancheta:** (a) passa a usar o desenho do Replay (disco cinza + seta), editável; (b) fica esmaecida como hoje. **Recomendo (a)**: é o visual único do cartão 22.
- **D5 · Qual lista ganha o botão de reescrever:** o bloco do Replay mostra os **momentos** (abertura perdida, morte isolada, virada numérica…), não os 6 tipos validados, que estão no **Perfil**. (a) botão nos momentos do bloco (protótipo) e nos chips do Perfil; (b) só nos momentos; (c) trocar os momentos do bloco pelos 6 tipos. **Recomendo (a)**.
- **D6 · Nome:** "Reescrever" ou "E se…?". **Recomendo "Reescrever"**: é o verbo do botão ("Reescrever este round", "Reescrever daqui"), e "E se…?" pede uma resposta ("o que teria acontecido"), que o site não pode dar.
- **D7 · O botão no cabeçalho do palco:** (a) "Reescrever este round" no cabeçalho e na barra; (b) só na barra, como hoje. **Recomendo (a)**: no modo palco a barra fica abaixo da dobra.

## 13. Observações do site no ar (fora do escopo, para o Iriun)
- O evento aparece como "IEM Krakw 2026" (sem o "ó") na landing, nas migalhas e no título; vem do nome da pasta da demo. O protótipo repete o que o site mostra.
- No bloco "Por que … perdeu este round" o tempo é o decorrido (0:12) e no resto do Replay é o relógio (1:42).
