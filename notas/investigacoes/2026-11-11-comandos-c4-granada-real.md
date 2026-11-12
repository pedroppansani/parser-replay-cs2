# C4: a granada real na aba Comandos (2026-11-11)

Decisão 64. Código: `dashboard/web/prancheta/20-comandos-granada.js` (a busca), `20-comandos.js` (o plano, a pergunta, o cartão), `scripts/comandos_contexto.py` (`GRANADA_REAL` e os textos).
Testes: `tests/test_comandos_granada.py`. Capturas: `scripts/design/capturas_comandos_c4.py`.

## Os números (da proposta, medidos na biblioteca `data/lineups`, sem o corpus)
- **A mesma jogada** (origem a 40 u, yaw e pitch a 3°, 14.696 arremessos): cai a 20 u do centro dela na mediana, 47 u no p75, 126 u no p90, 303 u no p95 (quicadas); sai a 9 u do centro dela na mediana, 28 u no p90 e 44 u no p99.
  Daí: queda a 150 u do destino; saída a 50 u é o mesmo lugar de lançamento (junta as jogadas e decide se a peça "já está lá").
- **Cobertura a 150 u na Mirage** (por ponto, mediana de arremessos por tipo): smoke 2, molotov 6, flash 6, HE 4; pontos com 5 ou mais: smoke 31%, molotov 58%, flash 61%, HE 43%. Dust2: 1, 4, 6, 3 e 29%, 49%, 58%, 38%.
- **A Caverna da Mirage** (o exemplo original): molotov a 150 u: 2 de TR e 88 de CT (a 200 u: 4 e 120). Por isso o aviso de lado e a frase "ct 2 joga molotov na caverna" trazendo a lista dos de CT.
- **Molotovs sem voo na biblioteca:** 148 de 5.694 (Mirage 30, Dust2 26, Nuke 13, Inferno 28, Anubis 23, Ancient 15, Overpass 5, Train 8). Ficam "não sei quando ela cai".
  A trajetória do projétil (do soltar ao último ponto) bate com o voo medido pelo fogo em 95,9% dos 5.568 molotovs com voo (erro de 0,02 s); os 4,1% restantes são do corte da medição (o id da entidade se repete
  no round e a trajetória sai 47 a 79 s mais longa). Cartão: medir o voo desse jeito, resolvendo o id repetido.
- **Flash:** a biblioteca grava o último ponto do projétil, onde ela estoura; compara-se só em xy, com o mesmo raio. O voo é conhecido em 99,9%.
- **Peso:** a biblioteca já carrega depois de a tela montar; a busca é linear (uns 2 mil arremessos por tipo) e nenhum índice novo entra no build.

## A impressão dos números
Antes (C3 mesclada) 18.480 linhas; depois 18.520: 40 novas (`comandos.granada.*`, 4 constantes por página), 0 mudaram, 0 sumiram.

## Testes de C2/C3 alterados na C4 (aprovados pelo Pedro)
Quinze testes tocados; 12 só trocam `pg.click("#pr-cmd-aplicar")` por `_aplica(pg)` (responde "sem arremesso real" a qualquer pergunta da granada e clica no Aplicar). Três mudaram asserção (`tests/test_comandos_aba.py`):
1. `test_o_exemplo_do_pedro_aplicado_vira_um_lote_e_um_desfazer_volta_tudo`: antes `"Ainda não busco o arremesso real" in #pr-cmd-origem`; agora `"Sem arremesso real: a granada sai de onde o jogador está" in #pr-cmd-origem` (texto mudou na C4), mais a asserção nova de que a pergunta da granada aparece.
2. `test_a_pergunta_recebe_o_foco_e_o_cartao_acompanha_a_tatica`: antes `is_enabled(Aplicar) and "ainda não está no mapa" not in resultado`; afrouxei para só a segunda metade e corrigi: agora responde "sem arremesso real" e exige as duas de novo.
3. `test_a_granada_que_sobra_depois_do_corte_e_mantida_e_o_cartao_avisa` (`test_comandos_tempos.py`): asserções intactas; só entrou `_sem_arremesso_real(pg)` antes delas, duas vezes.

## Cartão: times sem nome conhecido
Nove partidas aparecem como "Time de <jogador> × Time de <jogador>" (match_01 a match_09; ex. match_06 "Time de adamS × Time de -_-siNNer"). Proposta: tabela pequena de nomes de time, versionada, com teste (como a dos nomes de evento).
