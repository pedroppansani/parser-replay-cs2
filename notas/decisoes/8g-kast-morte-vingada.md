# Decisão 8g: O T do KAST vai para quem teve a MORTE VINGADA

- **ID:** 8g
- **Status:** vigente
- **Data:** 2026-09-22
- **Resumo:** O T do KAST é de quem teve a morte vingada (janela de 5 s).

## O que vale hoje

As contagens de KAST idêntico citadas no texto (24 de 30, 230 de 310) são das épocas em que foram medidas. A atual está em `data/processed/numeros_citaveis.json` (bloco `escada`).

## Texto

8g. **O T do KAST vai para quem teve a MORTE VINGADA.** Até aqui o KAST
   marcava a vítima do kill de trade -- o inimigo que matou e morreu na troca,
   que já tinha o K --, e o T nunca acrescentava nada: trocar a janela de 3s
   para 10s não mudava um único KAST, e o KAST ficava ~5 pontos abaixo do da
   HLTV. Corrigido (`basic_metrics.traded_deaths`), a janela de 5s que o projeto
   já usava é a que mais bate: 24 de 30 jogadores com KAST idêntico ao da HLTV
   em 3 partidas conferidas, erro médio 1,2 ponto (antes, 13 de 30 e viés de
   -4,5). O mesmo `was_traded` alimenta o carrega piano de TR e as "mortes
   trocadas" do perfil, que também estavam desligados. Não é feature do KMeans.
   **Assistência por flash não é o A do KAST**, como na HLTV (decisão do
   Pedro): contra o KAST oficial de 50 jogadores, 38 idênticos sem ela e 33
   com ela.
   **Os 12 que não batem foram investigados (Fase B) e nenhuma regra os
   explica** -- não mude a definição sem dado novo. 9 dos 12 têm KAST A MAIS
   (+1 ou +2), 3 a menos; não é categoria faltando (o A existe: assistência
   comum conta). Testado contra os 50, e todas pioram ou empatam os 38 atuais:
   janela de trade 3/4/6s; trade "por qualquer um" em vez de "por
   companheiro"; sobrevivência medida no fim do round em vez de na cauda;
   contar assistência por flash; KAST só no tempo regulamentar nas partidas
   com prorrogação (cai para 1 de 10); descontar sobrevivência ou trade
   isolados nos rounds de fronteira (12, 24, fim de prorrogação, último).
   Ninguém dos 12 deixou de jogar algum round. Os trades "a mais" se espalham
   de 0,02s a 4,8s, igual aos dos jogadores exatos: não é a janela.
   Com 310 KASTs oficiais (data/reference/hltv_componentes.json) o quadro se
   confirma: 230 de 310 idênticos (74%), excesso de +45 rounds, e o excesso
   está nos rounds creditados SÓ por trade (correlação +0,39; a HLTV não conta
   ~1 em 5 deles). Também descartados: marcar só a última ou só a primeira
   vítima de um matador que matou várias, e ignorar vingança depois do fim do
   round. A regra que separa esses trades não é recuperável dos dados.
   A hipótese "falta a assistência" também foi testada nos 310 e cai: o A já
   conta (assistência comum), 59 dos 80 errados têm KAST A MAIS -- categoria a
   menos não explica excesso --, e dos 21 abaixo só 1 fecha com flash assist.
   Assistência por dano (quem feriu a vítima que um companheiro matou) com
   limite de 41 dá os mesmos 230 (41 é o limite do próprio jogo); sem limite,
   129. O "caso isolado sem explicação" que estava aqui (SH1R0 na match_38, 13 contra 16
   oficial) era ERRO DE TRANSCRIÇÃO no gabarito, não no código: o 76,2% era o KAST do
   donk, duas linhas acima no mesmo print. O Detailed stats colado pelo Pedro em
   2026-09-22 dá 61,9% (13) nos dois formatos, com o mesmo Swing; corrigido.
