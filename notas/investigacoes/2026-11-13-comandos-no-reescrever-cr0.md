# Comandos dentro do Reescrever: proposta (CR0)

Só proposta: nenhuma mudança no site. Leitura de `dashboard/web/partida/10-reescrever.js` e `11-reescrever-granada.js`, `leitura/reescrever.py`, as decisões 55 a 64 (D1 a D7 em `notas/design/reescrever/especificacao.md`) e o código da aba Comandos (`comandos/leitor.js`, `prancheta/20-comandos*.js`, `scripts/comandos_contexto.py`). Os exemplos rodaram no leitor de hoje (node, contexto do Mirage, 610 pontos do Pedro, só os conferidos) e no `replay.json` da match_43. Scripts de apoio ficaram fora do repositório.

## O fato que muda a conta (vale ler antes dos itens)
O Reescrever de hoje guarda **um único ponto de destino por peça** (`edicoes[nome] = {x, y}`): a peça parte do instante do "Reescrever daqui" em linha reta e fica lá (decisão 58). Não existe horário próprio de uma edição. A aba Comandos da prancheta, ao contrário, monta **trilhas com horário** (várias paradas, "fica em X até H", "e depois"). Por isso "aos 0:50" não cabe no modelo atual: é preciso dar à peça uma **trilha** (`[{t, x, y}]`), em que até o primeiro horário ela segue o caminho REAL (o dado existe: `p.x[f]`, `p.y[f]`) e só depois diverge. A edição por arrastar vira o caso de uma parada no instante (mesma conta de hoje, testes do R2 e do R3 sem mudança).

## 1. Quem
- **Nick** (sem caixa, sem acento, `_` e `-` contam como separador): os 10 nicks do round entram no índice do leitor como os nomes de lugar entram hoje (chave de palavras: "donk666" e "donk 666" valem o mesmo). **Nick parcial**: só se for prefixo de uma palavra do nick, com 4 letras ou mais, único entre os 10 e que não seja palavra do leitor nem nome de lugar. O nick inteiro ganha do vocabulário.
- **Número**: "TR 2" e "CT 4" valem pela posição na coluna do banco (a ordem do `replay.json`, que o jogador já vê; no round 23: TR 1 mezii, TR 2 ropz, TR 3 apEX, TR 4 flameZ, TR 5 ZywOo; CT 1 molodoy, CT 2 FalleN, CT 3 KSCERATO, CT 4 yuurih, CT 5 YEKINDAR). "jogador 4" e "o 4" não dizem o lado: o leitor **pergunta** com botões que mostram o nick e a vida ("yuurih · CT 4" / "flameZ · TR 4, morto às 1:42").
- O cartão **sempre repete o nick** ("TR 2 = ropz"). A ordem do banco não é número de camisa de CS2: por isso o nick é o jeito principal e o número é só atalho.
- **Nicks parecidos:** no corpus (52 partidas, 122 nicks) **nenhuma** partida tem dois nicks que um comecem igual ao outro; mas dois nicks colidem com nome de lugar do Pedro no Dust2 ("FalleN" e "Niko" são pontos do mapa) e "MolO11" tem a palavra "molo" (sinônimo de molotov). Regra, a mesma do C1: ambíguo **nunca** é resolvido em silêncio: pergunta "FalleN é o jogador ou o lugar?"; sem aproximação por erro de digitação ("zywo" não vira ZywOo: o leitor de hoje responde "Quem faz...?" e marca a palavra sobrando; a CR propõe oferecer o nick mais parecido como botão, nunca como escolha).

## 2. Quando
- **Confirmado:** o Reescrever usa o relógio que a tela mostra, o mesmo do resto do Replay: o do round, descendo, e **depois do plant o da bomba** (decisão 60, cartão 28; `relogioDe` / `MapCore.relogio`). O leitor de hoje converte "0:30" sempre como relógio do round (115 − 30 = 85 s). No round 23 o plant foi aos 79,5 s; "0:30" na tela depois do plant é o relógio da bomba (89,5 s do início), 4,5 s depois. Proposta: a pergunta "N segundos contados como?" do C1 ganha a opção "relógio da bomba" quando o round tem plant e o horário é de 0:40 para baixo. O cartão mostra os dois: "aos 0:50 (relógio do round, 65 s do início)".
- **Antes do instante** (no round 23, "Reescrever daqui" em 1:20; "aos 1:30" vem antes): o cartão não aplica nem desloca em silêncio: "1:30 é antes de 1:20, onde a sua versão começa. Antes disso o real não muda." com **[Começar em 1:20]** e **[Corrigir]**. Comando sem horário: o leitor já pergunta; ganha o botão "No instante (1:20)".

## 3. A morte real (D3)
- **Comando que começa depois da morte real** do jogador: **recusado**, nunca "aplicado até a hora da morte" (seria inventar o que ele faria). Texto: "No real, {nome} morreu para {matador} às {h}. Depois disso a peça dele só existe no real; o site não refaz esse duelo. Escolha um horário até {h}." com **[Usar {h}]**. É a frase `mudou_morreu` de hoje, em forma de pergunta.
- **Comando que começa antes da morte e termina depois** (ex.: a corrida chega depois): aplicado; a peça anda e fica esmaecida na hora da morte real (✕ no fantasma) e "O que mudou" diz o `mudou_morreu`. Jogador já morto no instante: não se escolhe (o banco já diz "morto às 1:42, antes de 1:20").
- A morte de quem a sua versão **não** moveu e que morreu para alguém movido continua como no real, com o aviso `mudou_d3`.

## 4. Granada e inventário
O dado do site não tem o inventário de cada instante. **Recomendo (a):** o comando **só troca** uma granada que o jogador jogou de verdade neste round depois do horário (`n.by`, tipo igual), pelo mesmo critério do "Trocar a granada" do R4 (mesmo tipo e lado, saída a até 150 u de onde ele estava, voo conhecido); a nova sai no instante da original. Se não houver: "{nome} não jogou smoke depois de {h} neste round; o site só troca granadas que ele jogou." (nunca "ele não tinha"). (b) fica fora: o aviso "o site não sabe se ele tinha" é honesto mas deixa o usuário planejar o que talvez nem exista, contra a regra "plano, não previsão". Quando valer a pena: o inventário sai de compra + pegadas − arremessos (parquets do `interim`), mas não vai para a página hoje: seria uma fase de dado antes de qualquer (b).
Dado real: no round 23 "FalleN joga smoke no Janelão aos 0:57" acha a smoke dele de 0:57, mas a biblioteca tem **3** smokes de CT que caem no Janelão e a saída mais perto está a **663 u** de onde ele estava (o R4 exige 150 u): o cartão diz "nenhum arremesso real de CT cai no Janelão saindo de perto de onde FalleN estava".

## 5. Tempo e arremesso real
Funcionam igual, com um ponto de partida novo: a posição REAL da peça no instante do comando (interpolada em `p.x`, `p.y`), em vez da ficha da prancheta. `cmdTempoReal` (C3) só precisa de x, y, andar e do índice dos tempos do corpus (`tempos/<mapa>.js`, 20 KB no Mirage, carregado quando o painel abre, como a biblioteca do R4); a busca da C4 (`cmdBuscaReal`) usa a biblioteca que o R4 já carrega e o **lado real** da peça (melhor que o rótulo da ficha). Muda: (i) o lado vem do dado, sem palpite; (ii) o "levar até a saída" da C4 vira um trecho da trilha; (iii) a velocidade é a do Reescrever (rifle/AWP pela arma na mão), não a do jeito de andar.

## 6. "O que mudou" e o fantasma
Cada comando aplicado vira as **mesmas estruturas de hoje** (trilha da peça, troca de granada), então "O que mudou" e o fantasma funcionam sem mudança de desenho: o movimento (de onde, a que horas, quando chega), a morte do real (D3) e a granada trocada. Acrescento uma linha por comando aplicado, com a frase que o site entendeu ("ropz corre até Meio às 1:10, chega às 1:06 (estimado)"), e **só** isso. O fantasma continua o real onde difere por 8 u ou mais.

## 7. Onde fica o painel (rascunho)
Na coluna da direita do modo (`.painel-rw`), **entre a dica e "O que mudou"**, uma seção "Comandos" (uma frase, "Entender", o cartão "O que entendi", uma pergunta por vez, "Aplicar" e "Corrigir"), no violeta do modo. Computador: a coluna já tem `contain: size` e rola por dentro, então o mapa e a linha do palco não mudam de tamanho nem de lugar (D1). Celular: a coluna desce para baixo do mapa e pode crescer; o campo usa 16 px (sem zoom do iOS); o Real | Sua versão do R6b continua em cima. Teste de CLS 0 e de "o mapa não se mexe ao abrir o cartão" nos 3 tamanhos, como o do R6a. Pede-se um "Desfazer" no painel (o Reescrever de hoje só tem "Voltar ao real"): uma pilha de fotografias de `{trilhas, trocas}`, dois objetos pequenos.

## 8. O código, sem duplicar
- Já é puro e compartilhável: `comandos/leitor.js` (32 KB; carregado sob demanda, como `tempos/`), `scripts/comandos_contexto.py` (o contexto vem pronto do Python; a página da partida ganha `PAGINA.comandos` para o mapa dela: pontos, áreas, textos, parâmetros, e os 10 jogadores com nick, lado e número).
- **Não é compartilhável hoje:** `cmdPlano` (150 linhas), `cmdTempoReal` e `cmdBuscaReal` moram no escopo da prancheta (`S.estado`, `M3`, `cfg`, `funcaoDe`; 16 usos). Para os dois usarem o mesmo código, o plano vira um módulo puro (`comandos/plano.js`: `planeja(leitura, mundo)`, em que `mundo` dá `posicaoEm`, `velocidade`, `tempo real`, `biblioteca`), e a prancheta e o Reescrever só escrevem o adaptador.
- **Precisa mexer na prancheta?** Sim, nesse extrair. Garantia: (1) os testes da C1 a C4 **sem mudança**; (2) uma prova byte a byte, antes de qualquer tela: as operações que o `cmdPlano` de hoje devolve para as 7 situações da C4 e as frases da C2 e da C3 têm que ser idênticas às do módulo novo; (3) as capturas da C4 comparadas por hash. Sem essa prova a extração não entra; a alternativa (copiar o plano e aceitar duas cópias) está nas decisões.

## 9. Fases
- **CR1a:** extrair o plano, o tempo real e a busca para módulos puros, prancheta idêntica (prova byte a byte). Sem tela do Reescrever.
- **CR1b:** o leitor com os 10 nicks, número e regras do real (antes do instante, depois da morte, relógio da bomba), a trilha no núcleo do Reescrever (arrastar continua idêntico), testes e as 10 frases em nota. Sem tela.
- **CR2:** o painel Comandos (computador e celular), Desfazer, o cartão, as capturas nos 3 tamanhos e nos dois temas, todas abertas.
- **CR3:** a granada (troca), com a busca da C4 e o "levar até a saída".

## 10. Os 10 exemplos (match_43, round 23, Mirage; "Reescrever daqui" em 1:20)
Rodei no leitor de hoje com "TR 5"/"CT 4" no lugar dos nicks (a parte de nick é a nova); a coluna "regra do real" é a proposta.

| # | frase | o que o leitor entende | regra do real |
|---|---|---|---|
| 1 | "ZywOo roda pra B aos 0:50" | ZywOo (TR 5), mover até B, 0:50 = 65 s | **recusa**: ZywOo morreu às 0:53 (para molodoy); 0:50 é depois. [Usar 0:53] |
| 2 | "o 4 joga smoke no janelão aos 1:05" | quem sem lado, smoke, Janelão, 1:05 | pergunta "qual 4?": yuurih (CT 4) ou flameZ (TR 4, morto às 1:42, não editável). Com yuurih: ele não jogou smoke depois de 1:20 (jogou molotov, flash e smoke, todas antes): recusa de (a) |
| 3 | "FalleN joga smoke no janelão aos 0:57" | FalleN (CT 2), lançar smoke, Janelão, 0:57 | acha a smoke dele de 0:57; 3 arremessos de CT no Janelão, o mais perto sai a 663 u de onde ele estava: "nenhum arremesso real perto" |
| 4 | "ropz e apEX correm pro meio aos 1:10" | TR 2 + TR 3, mover até Meio, 45 s | ok: 1:10 é depois de 1:20 e os dois vivem; partem da posição real às 1:10; tempo real do corpus ou estimado, dito na tela |
| 5 | "mezii segura a caverna até 0:45" | TR 1, segurar Caverna, até 0:45 | ok: começa em 1:20 (instante) e a peça fica até 0:45 (o real dele morre às 0:34, depois) |
| 6 | "ropz vai pro B e depois pro meio" | 2 passos; pergunta "Quando começa?"; "pro meio" sem verbo pergunta o que faz (limite do C1) | botão "No instante (1:20)"; encadeia como na prancheta |
| 7 | "YEKINDAR corre pro meio aos 1:30" | CT 5, mover até Meio, 1:30 | 1:30 é antes de 1:20: [Começar em 1:20] [Corrigir]; o real não muda |
| 8 | "flameZ roda pra A aos 1:15" | TR 4, mover até A, 1:15 | recusa: flameZ morreu às 1:42, antes do instante; só existe no real |
| 9 | "molodoy corre pro B aos 0:40" | CT 1, mover até B, 0:40 | recusa: morreu às 0:47 (para apEX); 0:40 é depois. [Usar 0:47] |
| 10 | "KSCERATO corre pro meio aos 0:30" | CT 3, mover até Meio; o leitor de hoje conta 85 s (relógio do round) | pergunta: relógio da bomba (89,5 s, 10 s depois do plant) ou do round (85 s)? |

Extras que o leitor de hoje já cobre: "zywo roda pra B aos 1:00" (digitado errado) responde "Quem faz...?" e marca "zywo" como palavra sobrando.

## Decisões abertas para o Pedro
1. **"o 4" sem lado:** (a) perguntar sempre (recomendo; consistente com o C1, com botões de nick e vida); (b) aceitar quando só um dos dois está vivo no instante e mostrar no cartão.
2. **Comando depois da morte real:** (a) recusar (recomendo); (b) aplicar "até a hora da morte" (inventa o que o jogador faria).
3. **Granada:** (a) só trocar uma granada que ele jogou (recomendo); (b) permitir nova com o aviso fixo (exige antes o dado de inventário); (c) (a) agora e (b) numa fase de dado depois.
4. **Relógio depois do plant:** (a) a tela como está, com a pergunta "bomba ou round?" quando houver dúvida (recomendo); (b) sempre o relógio do round (diverge do que se vê).
5. **O plano:** (a) extrair para módulo puro com prova byte a byte (recomendo; evita duas cópias, mexe na prancheta sob a prova); (b) escrever um plano só do Reescrever e deixar a prancheta intocada (zero risco agora, duas cópias para manter).
6. **Desfazer no Reescrever:** (a) acrescentar a pilha de fotografias (recomendo; um comando = um desfazer, como pedido); (b) só "Voltar ao real".
7. **Carregar o leitor:** (a) sob demanda, como `tempos/` e a biblioteca (recomendo: 32 KB + 24 KB de contexto por mapa fora das 52 páginas); (b) dentro da página.
8. **Número no banco:** mostrar um número pequeno ao lado do nick no banco (recomendo, para "TR 2" ser descobrível) ou deixar só o nick.
