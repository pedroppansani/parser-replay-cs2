# CR2: a seção "Comandos" dentro do Reescrever (2026-11-13)

Terceira entrega da proposta da CR0 (`2026-11-13-comandos-no-reescrever-cr0.md`), em cima da CR1a (plano), CR1b (trilha com horário), CR1c (leitor com nicks e regras do real) e CR1d ("até" é o fim).

## O que entrou
- **Seção "Comandos"** na coluna da direita do modo, entre a dica e o resto. A casca (título que abre e fecha, campo, Entender, Aplicar, Corrigir e o espaço do cartão) está em `dashboard/web/partida/12-reescrever-comandos.js`; os arquivos pesados só são pedidos quando a seção abre ou o campo recebe o foco: `comandos/leitor.js`, `plano.js`, `real.js`, `reescrever.js` (a tela do cartão) e `comandos/real/<mapa>.js` (o contexto: pontos, áreas, textos). Gerados por `scripts/build_reescrever_comandos.py` (o `build_site` chama).
- **O cartão "O que entendi"** tem altura fixa (22 rem no computador, 15 rem no celular) e rola por dentro: abrir, entender, perguntar, aplicar e desfazer não empurram nada. Sempre mostra o nick ("ropz (TR 2)"), os vereditos da CR1c com os botões, o aviso de "termina depois da morte", a pergunta "bomba ou round?" (uma vez só por comando) e as perguntas com os botões de nick e vida. O foco vai para a pergunta quando ela aparece.
- **Aplicar** transforma o plano em paradas da trilha (`reescrever.trilha.define`, CR1b): cada trecho parte do instante em que a peça estava no ponto anterior; "fica até H" é só o intervalo entre duas paradas. A peça já editada mantém o que tinha antes do comando.
- **Desfazer** (ao lado de "Voltar ao real"): um item por comando, mesmo que mexa em várias peças; devolve exatamente a trilha de antes das peças que o comando tocou. "Voltar ao real" zera a pilha.
- **"O que mudou"**: uma linha por comando aplicado ("Comando: ropz (TR 2) · correndo até Meio · aos 1:10 · chega às 1:03 (linha reta, velocidade medida)"); o trecho que veio de um comando não repete a linha de movimento. A morte real, o plant e as granadas do real seguem como antes. O fantasma do real continua por baixo.
- **Número no banco** ao lado do nick (a ordem da coluna: "TR 2" = o segundo da coluna TR), só no modo Reescrever.
- **Granada fica para a CR3**: qualquer comando "joga ..." não é aplicado (nem a parte de movimento da mesma frase) e o cartão diz "Trocar granada por comando ainda não está pronto. Use 'Trocar a granada' na peça. Nada mudou."

## Decisões minhas, para conferir
- Os tempos de chegada são os do Reescrever, não os do corpus: o plano roda com `velocidadePiso` = a velocidade medida da arma na mão (a mesma da trilha), sem a tabela de tempos reais do C3. Assim o horário que o cartão diz é o que a peça faz. "Anda" e "agacha" usam a velocidade própria (as constantes da C3: rifle 111,8 e 90,4 u/s, AWP 104,0 e 82,4; correndo 210,6 e 197,1): cada parada da trilha pode levar o seu `modo`.
- Troca de andar por comando (Nuke): o cartão recusa dizendo que o Reescrever ainda não leva a peça de um andar a outro.
- Dois ganchos opcionais novos no `plano.js` (`velocidadePiso`, `aoAnotar`): a prancheta não os define e a bateria da CR1a continua igual byte a byte.
- O CSS da seção mora no `template.html` (só a página da partida), não no `v2.css` (que as pranchetas também carregam), para o HTML das pranchetas não mudar.

## Prova
- Testes existentes sem mudança: R2 a R6b, sugeridos, C1 a C4, CR1a a CR1d: 282 passaram.
- Novos (`tests/test_reescrever_comandos.py`, 22): rede (nada de `/comandos/` antes de abrir a seção; os 5 arquivos ao abrir; nada de novo ao fechar e abrir), campo com foco, erro de rede dito sem travar, número do banco só no Reescrever, mapa idêntico em 10 estados nos 3 tamanhos, CLS 0 (rigoroso: nem os deslocamentos logo depois de um clique, exceto abrir/fechar a seção, aplicar e desfazer, que movem "O que mudou" como no R3 e contam pelo padrão da página), aplicar e desfazer voltam exatamente (estado e "O que mudou"), desfazer com arrasto antes, a sua versão tocando desliga tudo, os 10 exemplos do round 23 de ponta a ponta na tela, "termina depois da morte" com a peça esmaecendo, ponto final separa comandos, acessibilidade (região anunciada, foco na pergunta, Tab e Enter, reduzir movimento).
- Prancheta idêntica: bateria do leitor (hash `f93a18ca03c11fca`) e do plano (`a2b36acb17f5780f`) iguais aos do `main` depois da CR1d; no site gerado, 88 dos 141 arquivos iguais byte a byte (as 12 pranchetas, `index`, `jogadores`, `reescrever.html`); mudaram só as 52 páginas de partida (+15,9 KB cada, 0,4 a 0,7 %) e o `comandos/plano.js` (+194 bytes); 10 arquivos novos.
- Capturas (round 23, "Reescrever daqui" 1:20, 3 tamanhos, 2 temas, 62 imagens): `notas/logs/capturas-cr2/` (`scripts/design/capturas_reescrever_cr2.py`).

## Ajustes do Pedro depois das capturas
1. O cartão, a pergunta e o veredito aparecem à vista: o cartão rola até o bloco e a coluna do painel (só ela, nunca a página; os `focus()` usam `preventScroll`) rola até o cartão. Teste a 1366x657: texto e botões do veredito, os botões da pergunta e o cartão entendido dentro da coluna e da janela, sem a página rolar.
2. Quem já morreu, na pergunta "de qual time é o 4?", continua como botão, mas desligado, com o motivo no rótulo; o foco vai para o primeiro que serve.
3. O arrasto (mouse e teclado) é um item próprio do Desfazer, como um comando: Desfazer sempre desfaz a última ação. Só o comando tem linha em "O que mudou".
4. "Anda" e "agacha" com a velocidade própria, no plano e na trilha (`velocidade_modos` no `PAGINA.reescrever`); o cartão diz o jeito que a peça faz.
5. "Não consegui aplicar" diz a causa: "o round acabou às {h} e {quem} só parte às {h}" ou "{quem} já está nesse lugar (a menos de 8 unidades)".
