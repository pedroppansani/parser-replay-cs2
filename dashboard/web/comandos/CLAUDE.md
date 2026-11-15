# dashboard/web/comandos/: leitor e plano dos comandos

Complementa o `CLAUDE.md` da raiz e o de `dashboard/web/`, e não os substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. Vale para `comandos/leitor.js`, `comandos/plano.js` e `comandos/real.js` (a prancheta e o Reescrever usam o mesmo).

- Leitor de comandos (`comandos/leitor.js`): puro (sem DOM, rede nem armazenamento); a frase de cada pergunta sai do Python
  (`scripts/comandos_contexto.py`); palavra desconhecida nunca vira alvo em silêncio; não calcula tempo de corrida (64)
- Plano dos comandos (`comandos/plano.js`): puro; recebe o "mundo" (`PlanoDeComandos.cria(W)`: estado da tática, relógio, peças, textos, biblioteca e tempos) e devolve o plano,
  o tempo real de corrida e a busca da granada real, o mesmo para a prancheta e (depois) o Reescrever. No site vem por arquivo, só quando a aba Comandos abre; a página gerada
  sozinha o traz embutido. O texto das funções não muda sem a prova `scripts/design/prova_plano_dos_comandos.py` (64)
- Comandos no Reescrever, sem tela (CR1c): o leitor entende nicks só quando o contexto os traz (sem diferenciar caixa e acento; parcial só com 4 letras ou mais, único e fora do
  vocabulário do leitor e dos nomes de lugar; nick que também é lugar do mapa sempre pergunta); `comandos/real.js` monta o elenco do round e dá o veredito de cada comando:
  começa depois da morte ou jogador já morto = recusado ([Escolher outro jogador], [Corrigir]); termina depois da morte = aplicado, a peça esmaece na hora da morte real;
  antes do instante = o real não muda; "bomba ou round?" só depois do plant. Sem nick no contexto (a prancheta) a leitura é a de sempre (64)
- "Até" é o FIM do `segurar` (CR1d): "segura o meio até 0:45" = fica no meio desde agora (ou desde o fim do comando anterior) até 0:45; "aos 0:45" continua sendo o início. O leitor devolve `quando: {tipo: "agora"}` e `fim: {t_decorrido}`; o plano para a peça no destino até o fim (e o comando seguinte parte dele); `esperar` e `mover` não mudam. "Agora" = marcador do tempo na prancheta, instante no Reescrever (`real.js`: `fim_antes_do_instante`, `termina_depois_da_morte`).
- Caminho das peças (`comandos/caminho.js`, PC1): puro, a mesma busca de `scripts/caminhos/busca.py`; carrega por arquivo (`caminhos/<mapa>.js`) só quando alguém precisa; nenhuma página o pede até a PC2, e o plano continua usando a reta até lá (70)
