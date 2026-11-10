# Decisão 64: Comandos na prancheta (os callouts do Pedro como dado e o leitor de frases)

- **ID:** 64
- **Status:** vigente
- **Data:** 2026-11-10
- **Resumo:** Os nomes de lugar que o Pedro usa (mapas de callouts dele) viram a tabela de alvos exatos; o nome do jogo em inglês também vale; o leitor de frases roda no navegador, é puro, só devolve o que entendeu e pergunta o que falta, sem chute; o tempo de corrida vem do corpus (20 casos e 3 partidas) e, sem amostra, é "estimado".

## Texto

64. **Comandos na prancheta** (C0, C0b e C1; pedido do Pedro, 2026-11-09 e 2026-11-10). Notas: `notas/investigacoes/2026-11-09-comandos-na-prancheta-c0.md` e `2026-11-09-comandos-callouts-do-pedro-c0b.md`.

- **Onde roda.** O leitor roda dentro do próprio site (`dashboard/web/comandos/leitor.js`): sem IA paga, sem servidor, sem chave, sem afrouxar o CSP. Nada é aplicado sem o Pedro confirmar; ambiguidade vira pergunta com botões; um comando aplicado é um desfazer (C2).
- **Alvo e chave do corpus.** O ponto do Pedro (`data/reference/callouts_br.csv`, de `pesquisa/comandos_c0b_callouts.py`) é o alvo exato de "vai até X" e de "molotov em X". O lugar da demo em que o ponto cai (`lugar_da_demo`) é a chave do tempo real do corpus. O nome do jogo em inglês também vale (sem diferença de maiúscula, espaço e acento), como alvo de área da demo; o ponto do Pedro ganha da área de mesmo nome. As imagens dos callouts são material de terceiros e NÃO entram no repositório (teste); só o nome e a posição. Cada linha tem `conferido` (sim só em Mirage e Dust2 até o Pedro avisar os outros mapas).
- **Tempo de corrida (C3).** Real do corpus quando há amostra: no mínimo 20 casos em 3 partidas (entre os dois pontos; senão entre as duas áreas da demo); abaixo disso, "estimado" (linha reta com `VELOCIDADE_U_S`), dizendo qual foi usado; mostra a faixa com o número de casos. O leitor NÃO calcula tempo. Troca de andar: a peça vai para o andar do ponto; sem amostra, o site diz que não estimou o tempo por causa da troca de andar, em vez de usar a linha reta.
- **Molotov real (C4).** Busca o arremesso real mais perto do destino, do mesmo lado, e oferece levar o jogador até o ponto de lançamento; a alternativa é pôr a molotov sem arremesso real, com o aviso.
- **Gramática (C1).** Entende "quem" (jogador N, TR/CT N, o N, função, ele), o quê (lançar, mover, segurar, esperar), onde, quando (relógio regressivo "aos 1:20" e "aos N s do início"; "N segundos" sem "do início" pergunta) e como (correndo, andando, agachado; "em N segundos" é duração imposta, só avisada). Cada campo que falta vira pergunta. Palavra desconhecida NUNCA é aproximada em silêncio: as sugestões parecidas vão como opções que a pessoa escolhe, e o alvo fica vazio. Nome repetido no mapa pergunta "qual?", a não ser que um qualificador ("default do A", "lixeira do CT", "banco do meio") resolva sozinho (o candidato mais perto do lugar citado, com folga de 25%). O contexto (pontos, áreas, jogadores, textos das perguntas) vem do Python (`scripts/comandos_contexto.py`, decisão 18); o leitor não toca no DOM nem na rede (teste).
