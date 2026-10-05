# Contexto do projeto para o Claude Code

Lido no início de cada sessão. Traz só o que está em vigor; o porquê de cada
regra, com o histórico, está em `notas/`.

## O projeto

Parser de replay (.dem) do CS2 que gera um site estático por partida (replay,
leitura da partida, perfil, prancheta tática). O parsing é do `awpy`; **o
diferencial é o desenho das métricas**: cada uma carrega uma decisão de jogo
explícita, e a validação final é o conhecimento de jogo do Pedro (Faceit 10,
flex AWPer). Ao propor ou mudar métrica, a justificativa de JOGO pesa tanto
quanto a corretude.

## Ambiente e como rodar

- Python 3.11 a 3.13 (`py -3.12` no Windows); o awpy 2.0.2 não suporta 3.14.
- O demo é 64 tick; nunca assuma (`metrics/timing.py` detecta).
- `py -3.12 -m pytest tests/` · `py -3.12 -m scripts.reprocessa` (corpus a partir
  do interim) · `py -3.12 -m scripts.build_site` · `py -3.12 -m scripts.escada_validacao`.
- Parse leva ~14 s por partida; itere com `--from-interim`.
- Sem o interim a partida não pode ser recalculada; apagar demo, interim ou
  backup segue a regra 36.

## Mapa do repositório

```
parsing/      wrapper do awpy, versões, verdade do arremesso
metrics/      as métricas (uma decisão de jogo por módulo) e as referências .json
clustering/   estilo de jogo por (jogador, round): PCA + KMeans global
leitura/      insights e frases da página
scripts/      pipeline, build, manifesto; calibracao/ validações
pesquisa/     exploratórios (teste não importa) · legado/ sem uso
dashboard/web template da página, map_core.js, annotations, tactics (prancheta)
tests/        testes (os de navegador usam Playwright)
data/processed  métricas por partida (versionado) · data/lineups  arremessos reais
data/interim    tabelas brutas (fora do git) · demos/  .dem (fora do git)
data/reference  dados oficiais da HLTV · notas/  decisões e investigações
docs/           site gerado (fora do git; artefato do CI)
```

## Convenções de código

- Comentários e docstrings em português.
- Toda métrica devolve `(per_round, summary)`; não troque o per_round pelo agregado.
- Limiar é constante nomeada no topo do módulo, com a origem ao lado.
- Polars e Parquet. `group_by` e `unique` sempre com `maintain_order=True`.
- Nada de texto fixo no `template.html` além da estrutura.
- Um commit por passo, com a suíte passando. Meça antes e depois. Teste existente
  não muda sem o Pedro aprovar.

## Regras vigentes

Uma linha por decisão em vigor; o ID é o que o código cita ("decisão 21a"). O
texto completo de cada uma está na nota do link (`notas/decisoes/`).

- [1](notas/decisoes/1-peek-hold-liquido.md) Peek ou hold pelo deslocamento LÍQUIDO; jiggle (sair e voltar) é hold.
- [2](notas/decisoes/2-peek-hold-posicao.md) Peek/hold usa a posição medida, não a flag `is_scoped`.
- [3](notas/decisoes/3-awp-no-trade.md) Tiro de AWP que erra sem custar a vida é `no_trade`, fora da conversão.
- [4](notas/decisoes/4-crosshair-contato.md) Crosshair placement só cobrado nas amostras antes de contato real (1 s).
- [5](notas/decisoes/5-angulos-por-moda.md) Ângulos de pré-fire: moda circular dos dados; nunca bins fixos.
- [6](notas/decisoes/6-desvio-de-setup.md) Desvio de setup: contra o padrão do próprio time, não um setup certo.
- [7](notas/decisoes/7-cluster-por-round.md) Clustering é por (jogador, round), não por jogador.
- [7a](notas/decisoes/7a-perfil-por-jogador.md) Perfil é a leitura; taxa com bruto, referência e amostra fraca.
- [7b](notas/decisoes/7b-features-comportamento.md) Clustering só com comportamento; resultado fica fora.
- [7c](notas/decisoes/7c-longe-do-time.md) "Longe do time": piso absoluto e nenhum companheiro no raio de apoio.
- [7d](notas/decisoes/7d-duas-camadas.md) Função estrutural (o trabalho) e traço comportamental (como) não se misturam.
- [7e](notas/decisoes/7e-funcoes-de-ct.md) Âncora, rotativo e coringa: dispersão do início × distância ao contato.
- [7f](notas/decisoes/7f-posicao-de-setup.md) Posição inicial: a de setup (10 s após o freeze), não o tick do freeze.
- [7g](notas/decisoes/7g-igl-manual.md) IGL nunca é atribuído automaticamente; vem de `roles_manual.json`.
- [7h](notas/decisoes/7h-trader.md) Trader é o segundo homem do entry; proximidade sozinha fica abaixo do piso.
- [8](notas/decisoes/8-kmeans-nao-nomeia.md) O KMeans não nomeia grupos; o nome é do Pedro (`cluster_names.json`).
- [8a](notas/decisoes/8a-tempo-desde-o-freeze.md) O tempo do timeline conta do fim do freeze; negativo é erro.
- [8b](notas/decisoes/8b-mortes-do-freeze.md) Freeze e intervalo: mortes e eventos não são de round nenhum.
- [8c](notas/decisoes/8c-sem-atacante.md) Sem atacante, o texto não nomeia ninguém; abertura é o 1º duelo ganho.
- [8d](notas/decisoes/8d-navegacao-por-tick.md) O replay navega por tick; fora da janela exportada, não navega.
- [8e](notas/decisoes/8e-dinheiro.md) Dinheiro só por `format_money` (`3.750$`).
- [8f](notas/decisoes/8f-round-de-faca.md) Round de faca sai no parse e os rounds são renumerados.
- [8g](notas/decisoes/8g-kast-morte-vingada.md) O T do KAST é de quem teve a morte vingada (janela de 5 s).
- [8h](notas/decisoes/8h-cegueira-reconstruida.md) Cegueira reconstruída de `flash_duration` sem `player_blind`.
- [8i](notas/decisoes/8i-economia-do-corpus.md) Economia do rating estimada no corpus, por arma mais cara e colete.
- [8j](notas/decisoes/8j-dano-no-mesmo-tick.md) `dmg_health_real` recalculado: acertos no mesmo tick não passam da vida.
- [9](notas/decisoes/9-convencao-de-angulos.md) Pitch positivo olha para baixo; o teste roda a invertida de controle.
- [10](notas/decisoes/10-paleta.md) Paleta validada (daltonismo, contraste); não trocar cor sem `valida_paleta`.
- [11](notas/decisoes/11-kmeans-global.md) KMeans ajustado uma vez no corpus (`global_model.json`), não por partida.
- [12](notas/decisoes/12-ancora-e-lurk-por-area.md) Âncora e lurk: por área do mapa (A/Mid/B), não por distância.
- [13](notas/decisoes/13-entry-e-acao.md) Entry é quem dá o primeiro contato do time, não quem chega cedo.
- [14](notas/decisoes/14-spawn-fora-da-particao.md) Spawn não é área de jogo; passagem rápida não é rotação.
- [15](notas/decisoes/15-carrega-piano.md) Carrega piano é produto de esforço por benefício, em três formas.
- [15a](notas/decisoes/15a-eixo-piano-baiter.md) Carrega piano e baiter: pontas de um eixo; rótulo só além de ±0,5.
- [15b](notas/decisoes/15b-repick-por-briga.md) Repick classifica cada briga; a junção inclui o tick da briga.
- [15c](notas/decisoes/15c-traco-dentro-da-funcao.md) Traço comportamental comparado dentro da função estrutural.
- [15d](notas/decisoes/15d-repick.md) Repick é jiggle mais evento no ângulo; o desfecho é campo à parte.
- [15e](notas/decisoes/15e-eixo-por-populacao.md) Cada braço do eixo piano/baiter contra a população da função.
- [15f](notas/decisoes/15f-funcao-do-round-no-pipeline.md) O pipeline passa a função do round aos papéis de comportamento.
- [16](notas/decisoes/16-escala-dos-papeis.md) A escala dos papéis é do corpus (`archetype_reference.json`).
- [17](notas/decisoes/17-empate-no-contato.md) Empate no primeiro contato não é abertura de ninguém.
- [18](notas/decisoes/18-frases-em-python.md) Frases dos cards saem do Python; papel sem sustentação: vazio.
- [19](notas/decisoes/19-round-decisivo.md) Round decisivo: maior variação da chance de vitória (modelo neutro).
- [19a](notas/decisoes/19a-decisivo-e-impressionante.md) Decisivo e impressionante: dois cards; pesos do segundo expostos.
- [19b](notas/decisoes/19b-sem-round-decisivo.md) Sem round decisivo é resultado; piso de 1,5× o round mais barato.
- [19c](notas/decisoes/19c-formato-pela-troca-de-lado.md) MR12 ou MR15 sai da troca de lado na demo.
- [19d](notas/decisoes/19d-economia-e-leitura.md) Economia é leitura ao lado do round decisivo, nunca peso.
- [19e](notas/decisoes/19e-prorrogacao.md) A prorrogação é modelada: o alvo sobe 4 a cada uma, até 5.
- [20](notas/decisoes/20-tres-blocos.md) A aba de leitura tem três blocos fixos; o MVP é o maior rating.
- [20a](notas/decisoes/20a-destaque-negativo.md) Destaque negativo só com número e referência.
- [20b](notas/decisoes/20b-bottom-frag.md) Bottom frag exige distância destacada (MAD); mochila exige vitória.
- [20c](notas/decisoes/20c-comparabilidade.md) Pontuação de função: "quanto acima do normal"; concentração ponderada.
- [20d](notas/decisoes/20d-empate-do-destaque.md) No empate do topo vence o destaque negativo.
- [21a](notas/decisoes/21a-arremesso.md) Botão, "no ar" e postura: da demo com `.dem`; inferidos sem ela.
- [21b](notas/decisoes/21b-console-no-jogo.md) Comando de console só é exato depois de conferido no jogo.
- [21c](notas/decisoes/21c-tick-oficial.md) Com `grenade_thrown`, o tick é a soltura; postura pela altura de saída.
- [22](notas/decisoes/22-rating-proprio.md) Rating: implementação própria do método do 3.0; nunca "o da HLTV".
- [22a](notas/decisoes/22a-swing-parametrico.md) O Round Swing usa regressão logística, não contagem por estado.
- [22b](notas/decisoes/22b-swing-por-desvio.md) O Round Swing é centrado em 1,00 e escalado pelo desvio.
- [22c](notas/decisoes/22c-faceit-nao-calibra.md) Partidas de FACEIT não servem para calibrar contra a HLTV.
- [22e](notas/decisoes/22e-rating-na-aba.md) O rating vai na aba Jogadores, com o modelo de round global.
- [22f](notas/decisoes/22f-swing-soma-zero.md) O Swing soma zero por evento e inclui o fim do round.
- [22g](notas/decisoes/22g-escada.md) Escada de validação: contagem exata antes de olhar o rating.
- [22h](notas/decisoes/22h-swing-oficial-soma-zero.md) Swing oficial soma zero; exceção: morte sem matador inimigo.
- [22i](notas/decisoes/22i-media-ou-desvio.md) Dividir pela média ou padronizar: mesmo rating com pesos ajustados.
- [22j](notas/decisoes/22j-detailed-stats.md) Degrau 4: aberturas, multi-kills e HS exatos; clutch é 1vX com X ≥ 1.
- [22k](notas/decisoes/22k-swing-sem-corte.md) Swing é variação de probabilidade pura; soma zero testa a integridade.
- [22l](notas/decisoes/22l-detalhes-do-rating.md) Escala alinhada, cálculo por lado, kill assistida e morte trocada.
- [23](notas/decisoes/23-anotacao.md) Anotação em coordenada de jogo; um ponto de redimensionar; sem texto no template.
- [24](notas/decisoes/24-saida-fora-do-git.md) `docs/` fica fora do repositório; o Pages é artefato do CI.
- [25](notas/decisoes/25-identidade-steamid.md) Identidade é o steamid; o nome é rótulo (`metrics/identidade.py`).
- [26](notas/decisoes/26-invariantes.md) Dez invariantes sobre o corpus inteiro (`test_invariantes_corpus.py`).
- [27](notas/decisoes/27-versoes.md) Cada partida grava a versão do parser (do interim), das métricas e o commit.
- [28](notas/decisoes/28-determinismo.md) Processamento determinístico: `group_by`/`unique` com ordem declarada.
- [29](notas/decisoes/29-lurker.md) Lurker: sem os rounds de AWP, relativo à função, mínimo de 8 rounds.
- [30](notas/decisoes/30-tres-niveis.md) Página da partida: números só dela; régua anônima do corpus; sem seletor.
- [31](notas/decisoes/31-pisos-de-funcao.md) Registro dos pisos de função e de onde veio cada um.
- [32](notas/decisoes/32-prancheta.md) Tática é log de operações; desfazer é `anula`/`reativa`; máquina de estados.
- [33](notas/decisoes/33-map-core.md) Um núcleo só para o mapa (`map_core.js`), aceito por pixel idêntico.
- [34](notas/decisoes/34-direcao-do-olhar.md) θ = −yaw; ângulo interpola linear pelo caminho curto.
- [35](notas/decisoes/35-reproducao-pura.md) Reprodução da prancheta: função pura do tempo.
- [36](notas/decisoes/36-preservacao-de-dados.md) Nenhum `.dem`, interim ou backup é apagado sem lista confirmada e cópia por sha256.
- [37](notas/decisoes/37-pagina-e-dado.md) Número de corpus em `numeros_citaveis.json`; dado passa por `esc()`; CI testa.
- [38](notas/decisoes/38-times-canonicos.md) Agregado por time usa o nome canônico (`metrics/times.py`).
- [39](notas/decisoes/39-rotulos-com-amostra-e-estabilidade.md) Rótulo: amostra mínima; estabilidade < 0,70 vira "tendência".
- [40](notas/decisoes/40-uma-regra-um-lugar.md) Trade, troca de lado, contato e AWPer do time: definidos uma vez.
- [41](notas/decisoes/41-impacto-e-jogadores.md) Impacto no perfil; entre partidas só em `jogadores.html`.
- [42](notas/decisoes/42-prancheta-no-tempo.md) Tática com horário toca no relógio; lugar pelo `place` do corpus.
- [43](notas/decisoes/43-round-real-na-prancheta.md) Round real é base travada; editar em t troca o real dali em diante.

## Números citáveis

Não cite número de cabeça. Os números do projeto (corpus, rating contra a HLTV,
escada, arremessos, testes) estão em `data/processed/numeros_citaveis.json`,
gerado por `py -3.12 -m scripts.numeros_citaveis`. README e landing leem dali.

## Pontos de calibração que pertencem ao Pedro

Não resolva nenhum destes sozinho; pergunte. Detalhe e histórico de cada um em
[`notas/calibracao.md`](notas/calibracao.md).

- Nomes dos grupos de estilo (`clustering/cluster_names.json`); conferir a cada reajuste.
- Partição A/Mid/B dos mapas (`MANUAL_PLACE_AREAS`); a Nuke é a mais frágil.
- Ângulos de entrada manuais (`MANUAL_ENTRY_ANGLES`).
- Janela de trade (5,0 s) e limiares de peek/hold, contato, pré-fire e rotação.
- Pesos da divisão de crédito do Round Swing e todos os pesos de `round_spectacle.py`.
- Altura dos olhos e diferença em pé/agachado medidas (regra 21c).
- Limiares do card de destaque, do round decisivo, da autópsia e dos papéis.
- Pisos de função (regra 31) e do eixo carrega piano/baiter; repick com mais de uma saída.
- Paleta dos gráficos (regra 10).
- Rota B: força intermediária (0,6141 afirma "médio"), agachamento parcial neutro,
  custo da tabela `movimento`. FACEIT: ligar `TICK_PELO_PROJETIL_SEM_EVENTO`.

## Pendências

- No jogo: [`PENDENCIAS_NO_JOGO.md`](PENDENCIAS_NO_JOGO.md).
- Demos a baixar: [`RECUPERACAO_DEMOS.md`](RECUPERACAO_DEMOS.md).
- Limitações conhecidas: [`notas/limitacoes.md`](notas/limitacoes.md).

## Glossário

- **Gabarito:** arremessos de partidas com `.dem`, com o que a demo grava (força,
  velocidade, postura, chão), em `tests/fixtures/gabarito_arremessos_*`.
- **Rota A:** inferir botão, "no ar" e postura só com posição, pela rotina do jogo medida no gabarito.
- **Rota B:** ler esses valores da demo (parser 2) e declarar a fonte de cada campo.
- **Neutro:** arremesso ou rótulo sem afirmação, com o motivo; nunca um palpite.
- **Catraca:** teste que grava o melhor valor medido e falha se piorar.
- **Fora da amostra:** avaliado em dado que não entrou no ajuste.
- **Regra 36:** preservação de dados (demo, interim e backup).
- Nas notas antigas, "item 7" é a investigação da força do arremesso, "etapa N"
  são as etapas da prancheta e "Fase X" são fases de trabalho anteriores.
