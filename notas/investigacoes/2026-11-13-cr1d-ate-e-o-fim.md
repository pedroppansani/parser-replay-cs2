# CR1d: "até" é o fim do "segura" (2026-11-13)

Decisão do Pedro: em "segura X até H", H é o FIM. "segura o meio até 0:45" = fica no meio desde agora (ou desde o fim do comando anterior) até 0:45. "segura o meio aos 0:45" continua sendo o início. Vale na prancheta e no Reescrever.

## O que mudou
- `leitor.js`: depois de "até", o horário de um `segurar` vira `acao.fim` (`{tipo:"relogio", segundos_restantes, t_decorrido}`); sem horário de início, `quando = {tipo:"agora"}`. Horário que não existe no round vira pergunta (`horario_invalido`, `para: "fim"`). `esperar` ("espera até 0:45") e `mover` ("corre até 0:45") não mudam.
- `plano.js`: "agora" = fim do comando anterior, ou o "agora" do mundo (`W.agora()`). A peça chega e fica no destino até o fim (ponto de espera em `fim`); o seguinte parte do fim. Fim antes da chegada: aviso `aviso_segura_curto`, sem ponto de espera.
- Prancheta (`20-comandos.js`): `agora` = marcador do tempo (`S.t`); cartão "desde 1:55 · até 0:45" (`linha_segurar_ate`).
- Reescrever (`real.js`): "agora" no primeiro comando = o instante; o fim decide a morte (`termina_depois_da_morte` aplica e esmaece); fim antes do instante = `fim_antes_do_instante` (recusa, [Corrigir]); "bomba ou round?" também pergunta para o fim depois do plant.

## Prova
- Testes da C1 a C4 (leitor, tempos, granada, aba, documentados, plano, trilha, modo): 141 passaram, nenhum mudou. Único teste existente alterado: `exemplo_5` da CR1c (CR1c, não C1–C4), que usava "segura ... até" com a leitura antiga.
- Novo: `tests/test_comandos_ate_e_fim.py`.
- Leitor, bateria byte a byte (`prova_leitor_dos_comandos`): 250 diferenças de 2.050; as 250 são frases com "segura ... até horário" (checado por padrão). Horários: 48 iguais.
- Plano: 392 diferenças de 4.116 (frases e telas); todas "segura ... até horário"; buscas 1.080 iguais.
- Antes e depois de 5 frases: `notas/logs/cr1d-frases-antes.json` e `-depois.json`.
