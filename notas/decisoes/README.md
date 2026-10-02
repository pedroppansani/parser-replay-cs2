# Decisões

Uma nota por decisão. O `CLAUDE.md` traz a lista curta das que estão em vigor.

| ID | Status | Resumo |
|---|---|---|
| [1](1-peek-hold-liquido.md) | vigente | Peek ou hold pelo deslocamento LÍQUIDO; jiggle (sair e voltar) é hold. |
| [2](2-peek-hold-posicao.md) | vigente | Peek/hold usa a posição medida, não a flag `is_scoped`. |
| [3](3-awp-no-trade.md) | vigente | Tiro de AWP que erra sem custar a vida é `no_trade`, fora da conversão. |
| [4](4-crosshair-contato.md) | vigente | Crosshair placement só é cobrado nas amostras antes de contato real (1 s). |
| [5](5-angulos-por-moda.md) | vigente | Ângulos de pré-fire saem dos dados por moda circular; nunca bins fixos. |
| [6](6-desvio-de-setup.md) | vigente | Desvio de setup é contra o padrão do próprio time, não contra um setup certo. |
| [7](7-cluster-por-round.md) | vigente | Clustering é por (jogador, round), não por jogador. |
| [7a](7a-perfil-por-jogador.md) | vigente | O perfil por jogador é a leitura; taxa sempre com bruto, referência e marca de amostra fraca. |
| [7b](7b-features-comportamento.md) | vigente | Features do clustering são só comportamento; resultado (kills, dano) fica fora. |
| [7c](7c-longe-do-time.md) | vigente | "Longe do time" exige piso absoluto e nenhum companheiro no raio de apoio. |
| [7d](7d-duas-camadas.md) | vigente | Função estrutural (o trabalho) e traço comportamental (como executa) não se misturam. |
| [7e](7e-funcoes-de-ct.md) | vigente | Âncora, rotativo e coringa saem de dispersão do início × distância ao contato. |
| [7f](7f-posicao-de-setup.md) | vigente | Posição inicial é a de setup (10 s depois do freeze), não o tick do freeze. |
| [7g](7g-igl-manual.md) | vigente | IGL nunca é atribuído automaticamente; vem de `roles_manual.json`. |
| [7h](7h-trader.md) | vigente | Trader é o segundo homem do entry; proximidade sozinha fica abaixo do piso. |
| [8](8-kmeans-nao-nomeia.md) | vigente | O KMeans não nomeia grupos; o nome é do Pedro (`cluster_names.json`). |
| [8a](8a-tempo-desde-o-freeze.md) | vigente | O tempo do timeline conta do fim do freeze; negativo é erro. |
| [8b](8b-mortes-do-freeze.md) | vigente | Mortes e eventos do freeze time e do intervalo não pertencem a round nenhum. |
| [8c](8c-sem-atacante.md) | vigente | Sem atacante o texto não nomeia ninguém; abertura é o primeiro duelo ganho. |
| [8d](8d-navegacao-por-tick.md) | vigente | O replay navega por tick; fora da janela exportada, não navega. |
| [8e](8e-dinheiro.md) | vigente | Dinheiro só por `format_money` (`3.750$`). |
| [8f](8f-round-de-faca.md) | vigente | Round de faca sai no parse e os rounds são renumerados. |
| [8g](8g-kast-morte-vingada.md) | vigente | O T do KAST é de quem teve a morte vingada (janela de 5 s). |
| [8h](8h-cegueira-reconstruida.md) | vigente | Cegueira é reconstruída de `flash_duration` nas demos sem `player_blind`. |
| [8i](8i-economia-do-corpus.md) | vigente | Economia do rating estimada no corpus, por arma mais cara e colete. |
| [8j](8j-dano-no-mesmo-tick.md) | vigente | `dmg_health_real` é recalculado: vários acertos no tick não passam da vida. |
| [9](9-convencao-de-angulos.md) | vigente | Pitch positivo olha para baixo; o teste roda a convenção invertida como controle. |
| [10](10-paleta.md) | vigente | Paleta validada para daltonismo e contraste; não trocar cor sem `valida_paleta`. |
| [11](11-kmeans-global.md) | vigente | O KMeans é ajustado uma vez no corpus (`global_model.json`), não por partida. |
| [12](12-ancora-e-lurk-por-area.md) | vigente | Âncora e lurk são medidos por área do mapa (A/Mid/B), não por distância. |
| [13](13-entry-e-acao.md) | vigente | Entry é quem dá o primeiro contato do time, não quem chega cedo. |
| [14](14-spawn-fora-da-particao.md) | vigente | Spawn não é área de jogo; passagem rápida não conta como rotação. |
| [15](15-carrega-piano.md) | vigente | Carrega piano é produto de esforço por benefício, em três formas. |
| [15a](15a-eixo-piano-baiter.md) | vigente | Carrega piano e baiter são as pontas de um eixo; rótulo só além de ±0,5. |
| [15b](15b-repick-por-briga.md) | vigente | Repick classifica cada briga; a junção inclui o tick da briga. |
| [15c](15c-traco-dentro-da-funcao.md) | vigente | Traço comportamental é comparado dentro da função estrutural. |
| [15d](15d-repick.md) | vigente | Repick é jiggle mais evento no ângulo; o desfecho é campo à parte. |
| [15e](15e-eixo-por-populacao.md) | vigente | Cada braço do eixo piano/baiter é comparado com a população da função. |
| [15f](15f-funcao-do-round-no-pipeline.md) | vigente | O pipeline passa a função do round aos papéis comportamentais (regressão corrigida). |
| [16](16-escala-dos-papeis.md) | vigente | A escala dos papéis é do corpus (`archetype_reference.json`). |
| [17](17-empate-no-contato.md) | vigente | Empate no primeiro contato não é abertura de ninguém. |
| [18](18-frases-em-python.md) | vigente | Frases dos cards saem do Python; papel sem sustentação devolve vazio. |
| [19](19-round-decisivo.md) | vigente | Round decisivo é a maior variação da probabilidade de vitória (modelo neutro 0,5). |
| [19a](19a-decisivo-e-impressionante.md) | vigente | Decisivo e impressionante são dois cards; o segundo tem pesos expostos. |
| [19b](19b-sem-round-decisivo.md) | vigente | Partida sem round decisivo é resultado; piso de 1,5× o round mais barato. |
| [19c](19c-formato-pela-troca-de-lado.md) | vigente | MR12 ou MR15 sai da troca de lado na demo. |
| [19d](19d-economia-e-leitura.md) | vigente | Economia é leitura ao lado do round decisivo, nunca peso. |
| [19e](19e-prorrogacao.md) | vigente | A prorrogação é modelada: o alvo sobe 4 a cada uma, até 5. |
| [20](20-tres-blocos.md) | vigente | A aba de leitura tem três blocos fixos; o MVP mostra os componentes. |
| [20a](20a-destaque-negativo.md) | vigente | Destaque negativo só com número e referência. |
| [20b](20b-bottom-frag.md) | vigente | Bottom frag exige distância destacada (MAD); mochila exige vitória. |
| [20c](20c-comparabilidade.md) | vigente | Pontuação de função é "quanto acima do normal"; concentração ponderada. |
| [20d](20d-empate-do-destaque.md) | vigente | No empate do topo vence o destaque negativo. |
| [21](21-ancoragem.md) | substituída por 21c | Soltura por ancoragem geométrica. |
| [21a](21a-arremesso.md) | vigente | Botão, "no ar" e postura: lidos da demo onde há `.dem`, inferidos pela rotina do jogo onde não há. |
| [21b](21b-console-no-jogo.md) | vigente | O comando de console só é dado como exato depois de conferido no jogo. |
| [21c](21c-tick-oficial.md) | vigente | Com `grenade_thrown`, o tick do evento é a soltura; postura pela altura de saída. |
| [22](22-rating-proprio.md) | vigente | O rating é implementação própria da metodologia do Rating 3.0; nunca "o da HLTV". |
| [22a](22a-swing-parametrico.md) | vigente | O Round Swing usa regressão logística, não contagem por estado. |
| [22b](22b-swing-por-desvio.md) | vigente | O Round Swing é centrado em 1,00 e escalado pelo desvio. |
| [22c](22c-faceit-nao-calibra.md) | vigente | Partidas de FACEIT não servem para calibrar contra a HLTV. |
| [22e](22e-rating-na-aba.md) | vigente | O rating vai na aba Jogadores, com o modelo de round global. |
| [22f](22f-swing-soma-zero.md) | vigente | O Swing soma zero por evento e inclui o fim do round. |
| [22g](22g-escada.md) | vigente | Escada de validação: contagem exata antes de olhar o rating. |
| [22h](22h-swing-oficial-soma-zero.md) | vigente | O Swing oficial soma zero; as exceções são mortes sem matador inimigo. |
| [22i](22i-media-ou-desvio.md) | vigente | Dividir pela média ou padronizar dá o mesmo rating com pesos ajustados. |
| [22j](22j-detailed-stats.md) | vigente | Degrau 4: aberturas, multi-kills e headshots exatos; clutch é 1vX com X ≥ 1. |
| [22k](22k-swing-sem-corte.md) | vigente | O Swing é variação de probabilidade pura; soma zero é teste de integridade. |
| [22l](22l-detalhes-do-rating.md) | vigente | Escala alinhada, cálculo por lado, kill assistida e morte trocada. |
| [23](23-anotacao.md) | vigente | Anotação em coordenada de jogo; um ponto de redimensionamento; sem texto no template. |
| [24](24-saida-fora-do-git.md) | vigente | Saída gerada (`docs/`) não vai para o repositório; o Pages é artefato do CI. |
| [25](25-identidade-steamid.md) | vigente | Identidade é o steamid; o nome é rótulo (`metrics/identidade.py`). |
| [26](26-invariantes.md) | vigente | Dez invariantes sobre o corpus inteiro (`test_invariantes_corpus.py`). |
| [27](27-versoes.md) | vigente | Cada partida grava a versão do parser (lida do interim) e das métricas, e o commit. |
| [28](28-determinismo.md) | vigente | Processamento determinístico: `group_by`/`unique` com ordem; empate de função por 1 round. |
| [29](29-lurker.md) | vigente | Lurker: sem os rounds de AWP, relativo à função, mínimo de 8 rounds. |
| [30](30-tres-niveis.md) | vigente | Página da partida: números só dela; régua anônima do corpus; sem seletor. |
| [31](31-pisos-de-funcao.md) | vigente | Registro dos pisos de função e de onde veio cada um. |
| [32](32-prancheta.md) | vigente | A tática é um log de operações; desfazer é `anula`/`reativa`; interação por máquina de estados. |
| [33](33-map-core.md) | vigente | Um núcleo só para o mapa (`map_core.js`); extração aceita por pixel idêntico. |
| [34](34-direcao-do-olhar.md) | vigente | θ = −yaw; ângulo interpola linear pelo caminho curto. |
| [35](35-reproducao-pura.md) | vigente | A reprodução da prancheta é função pura do tempo. |
| [36](36-preservacao-de-dados.md) | vigente | Nenhum `.dem`, interim ou backup é apagado sem lista confirmada e cópia por sha256. |
| [37](37-pagina-e-dado.md) | vigente | Número de corpus vem de `numeros_citaveis.json`; texto do dado passa por `esc()`; CI testa antes de publicar. |
