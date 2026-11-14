# CR3: a granada por comando no Reescrever (2026-11-14)

Quarta entrega da proposta da CR0, em cima da CR1a a CR1d e da CR2. Vale a decisão (a) da CR0: **o comando só troca uma granada que o jogador jogou de verdade neste round**; o dado não tem inventário, então o site nunca cria uma granada nova.

## O que entrou
- **Qual granada é trocada** (`comandos/reescrever.js`, `veredictosDaGranada`): do mesmo tipo e do mesmo jogador, lançada DEPOIS do instante. Uma só = é essa; várias = o cartão pergunta qual, um botão por granada com o horário e o lugar reais ("flash das 0:55 em BOMBSITE A"); nenhuma no round = "No real, ropz não jogou smoke neste round. O site não sabe se ele tinha uma." + [Corrigir]; só antes do instante = recusada, com o horário dela (já faz parte do real).
- **O arremesso novo** vem da biblioteca (a mesma do R4 e da prancheta), pela busca da C4 sem mudança: mesmo tipo e lado, queda a até 150 u, "lugar de saída i de n" com partida e round, aviso de lado, voo desconhecido = "não sei quando ela cai". Sem arremesso para o destino: recusado e nada muda. **Não existe "Pôr a granada sem arremesso real"** no Reescrever.
- **A hora e a saída**: "aos 1:05" é a hora em que a granada sai da mão. Saída longe da peça: [Levar o ropz até lá] / [Usar outro arremesso] (a trilha da CR1b); chegada tardia: "Jogar às H?" (a peça não parte antes do instante: gancho `livreDesde`). A hora do arremesso vale para a morte real (recusa `gr_depois_da_morte`). Troca de andar continua recusada (só [Usar outro arremesso]).
- **Frase mista** ("apEX corre pro meio aos 1:10 e depois joga flash no meio"): aplica a corrida e a troca; um comando = um item do Desfazer, que devolve as trilhas E as trocas (`empurra(foto, linha, trocas)`).
- **"O que mudou"**: uma linha por troca ("FalleN troca a smoke das 0:57 em SCAFFOLDING por smoke em Janelão às 0:57 (lugar de saída 1 de 3, Vitality × Spirit, round 23); ela cai às 0:54, 2,3 s depois de sair da mão."). O fantasma mostra a granada real tracejada e o "cai 0:54" da nova. O aviso da CR2 ("ainda não está pronto") saiu.
- **Núcleo**: a troca por comando (`poeTroca` em `11-reescrever-granada.js`) leva o seu horário (`f0`) e o seu lugar de saída (`origem`) e vale com a peça editada (a ferramenta "Trocar a granada" continua como era). O voo desconhecido não desenha voo, queda nem zona. A biblioteca só é pedida por uma frase de granada já completa (sem pergunta aberta); quando chega, o foco só volta ao cartão se já estava nele.

## Decisões minhas, para conferir
- Peça que só joga de PERTO do lugar de saída (até 50 u) não anda: a granada sai do lugar de saída do arremesso, na hora do comando. No instante exato do "Reescrever daqui" ela sai uns 0,1 s depois (a peça não parte antes do instante).
- Quando há mais de uma peça na mesma frase de granada, as respostas "levar" e "jogar às" valem para o comando todo (como na prancheta).
- Mirage tem um andar só: o caminho "outro andar" não tem teste no navegador (o texto e a lógica são os do plano, já cobertos pela prancheta).
- Dois ganchos opcionais novos no `plano.js` (`livreDesde`, `aoLancar`): a prancheta não os define.
- Um defeito achado nas capturas: depois do Aplicar a troca não aparecia no mapa até algo redesenhar; `empurra` agora redesenha.

## Prova
- Testes existentes sem mudança: R2 a R6b, sugeridos, C1 a C4, CR1a a CR1d e CR2 (26 de 27). O da CR2 que mudou, a pedido: `test_exemplo_3_...` (antes: "comando de granada não aplica nada e diz que é a CR3"; depois: sem a biblioteca ou sem granada real, nada muda e o cartão diz o motivo). Antes salvo em `notas/logs/cr3-exemplo3-antes.txt`.
- Novos (`tests/test_reescrever_granada_comando.py`, 14): nenhuma granada sem uma real do mesmo tipo e jogador, antes do instante, qual granada (2 flash), mesmo tipo/lado/150 u, só do outro lado, sem arremesso para o destino, [Levar] + Desfazer volta exatamente, chegada tardia, morte real, frase mista, voo desconhecido, a sua versão tocando (sai na hora e cai depois do voo), rede (biblioteca só por frase completa), mapa e CLS 0.
- Prancheta idêntica: prova do plano (`prova_plano_dos_comandos`) 4068/4068 frases, 1080/1080 buscas, 48/48 telas, hash geral `a2b36acb17f5780f` igual ao do `main`; `leitor.js` e a prancheta sem diferença contra o `main`. A impressão dos números não foi tocada.
- Capturas (round 23, "Reescrever daqui" 1:20, 3 tamanhos, 2 temas, 42 imagens): `notas/logs/capturas-cr3/` (`scripts/design/capturas_reescrever_cr3.py`).
