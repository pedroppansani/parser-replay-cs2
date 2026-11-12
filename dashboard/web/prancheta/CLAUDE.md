# dashboard/web/prancheta/: cor, mapa, canvas e prancheta

Complementa o `CLAUDE.md` da raiz e o de `dashboard/web/`, e não os substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. Vale para `map_core.js`, o canvas, o Replay (`partida/`) e a prancheta (`prancheta/`);
`metrics/tactics.py` e `metrics/annotations.py` espelham o JS: estas regras valem lá também.

## Cor e mapa

- CT azul, TR dourado; cada granada mantém a forma do `nadeGlyph`; uma cor, um papel: cor de lado só
  para o lado (o do round), destaque só no verde do decisivo, vitória e link
  sem matiz; `--erro` e `--aviso` nunca marcam erro de jogador (44, 46)
- Tema: claro ou escuro escolhido na landing (`tema.js` no `<head>`, sem inline); prancheta sempre `violeta`; o
  canvas lê só `*-mapa` e granadas, iguais em todo tema; a moldura do mapa é a ilha `data-tema="escuro"` (48, 51)
- Cor nova ou trocada passa por `py -3.12 -m metrics.paleta` contra o fundo (texto
  4,5:1, marca 3:1, ΔE2000 ≥ 8 no pior par daltônico); o scatter de clusters segue facetado (10)
- Mapa, peças e granadas em canvas, com UM núcleo (`map_core.js`); `desenhaJogador` não ganha
  save/restore; lugares, outro andar, palco, Reescrever (33, 52, 53, 54, 57, 58, 59, 60, 61, 62, 63, 64)
- θ = −yaw só em `MapCore.anguloDeTela`; o ângulo interpola linear pelo caminho curto
  (`interpolaAngulo`), sem Catmull-Rom (34)
<!-- bloco anotacao-unidade-de-jogo: inicio -->
- Anotação guardada em unidade de jogo, com a impressão da calibração em cada traço; todo
  redimensionamento passa por `reprojetaTudo()`, nunca redesenha do que está pintado; espaço +
  arrastar move o mapa e nunca começa traço (23)
<!-- bloco anotacao-unidade-de-jogo: fim -->

## Prancheta

- A biblioteca de arremessos vem de `arremessos/<mapa>.js` depois da tela; quem a usa espera `quandoBiblioteca` (49)
<!-- bloco prancheta-espelho: inicio -->
- A tática é um LOG DE OPERAÇÕES aplicado na ordem (seq, autor, id); mesclar é a união por id;
  persistência só por `Armazem`; arquivo com formato, versão e calibração (outra é recusada); JS e
  Python chegam ao MESMO estado; versão antiga é migrada em memória sem mudar operação (32)
- Desfazer é só `anula`/`reativa`, do mesmo autor; nunca operação inversa por tipo; vida em PASSOS
  (`dura_passos`); ordem de criação é a do log, sem contador próprio; granada do round liga ao
  arremesso real, nunca por proximidade (32)
- Reprodução é função pura do tempo (`estadoNoTempo`; no relógio, `cenaNoRelogio`): arrastar até t e
  tocar até t dão o mesmo quadro; nada é editável durante ela (35, 42)
- Toca no relógio só a tática com operação do formato 3 ou granada com horário; a só com passos toca
  passo a passo; o significado de uma operação existente não muda (42)
- Granada desenhada é desenho (anel tracejado de tela, carimbo, corpo a 100%): sem horário, fora da
  linha do tempo e do roteiro; só "Converter em granada com horário" a torna evento (45)
- Toda operação que entra de fora (arquivo, tática guardada, sala, ao vivo) passa por `problemaDaOperacao`, espelhada em `metrics/tactics.problemas_da_operacao`: validador único, nunca um segundo (47)
- Operação nova da prancheta exige migração nova (`grupos.tipos_de_operacao()`, conferida contra `OPERACOES` do JS e do
  Python); o log do grupo é o estado inicial, numa linha, seguido das operações; os tetos de uso são do servidor (47)
<!-- bloco prancheta-espelho: fim -->
- Aba Comandos (`20-comandos.js`): Entender nunca muda a tática; Aplicar emite UM lote com operações existentes (um desfazer); tempo de corrida REAL do corpus quando há amostra (`data/tempos`, arquivo próprio carregado ao abrir a aba), senão um PISO ("não antes de": linha reta a 250 u/s correndo); a tela diz de onde veio; a granada puxa um arremesso real da biblioteca (mesmo tipo e lado, queda a 150 u, saída a 50 u da peça sem perguntar; `20-comandos-granada.js`); a ordem é a do relógio; troca de andar sem tempo real pergunta a chegada; a peça que ainda anda parte do ponto interpolado do plano (64)
- A interação é UMA máquina de estados (`ESTADOS`); atalhos num mapa único `ATALHOS`, sem tecla
  repetida (32)
- Ponto atrasado é CALCULADO do log (`atrasosDosPontos`) e nunca guardado; desenha-se em `--aviso` com
  "+N s" e texto equivalente; o contador de operações só em "Detalhes técnicos" aberto (35, 43)
- O round real é base travada (`origem.base_real`); editar um jogador em t corta o real dele depois
  de t e ancora o estado real em t; mover num round anda na velocidade medida; "Voltar ao real" anula
  pelo `anula` (43)
- Grupo só transporta o log, sem mudar operação; quem pode desenhar é o servidor (RLS): na recusa a
  operação sai do log local, sem `anula`; sem grupo nada vai à rede; o link `#sala=` nunca entra sozinho: com nick salvo a aba mostra um botão "Entrar no grupo da <mapa> como <nick>" e só o clique conecta (47)
