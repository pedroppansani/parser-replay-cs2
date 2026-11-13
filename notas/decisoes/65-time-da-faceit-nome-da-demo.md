# Decisão 65: O time da FACEIT usa o nome que a demo grava

- **ID:** 65
- **Status:** vigente
- **Data:** 2026-11-12
- **Resumo:** Na FACEIT o lado se chama "Time de <nick>", onde o nick é o do nome de time que a demo grava (`team_t1ltedbot` -> "Time de t1ltedbot"). Substitui a escolha do primeiro nick em ordem alfabética (decisão 28) só para esse caso; sem nome, com nome vazio ou genérico, ela continua valendo como reserva.

## Texto

65. **O nome do time da FACEIT** (pedido do Pedro, 2026-11-12, na P1c; investigação em `notas/investigacoes/2026-11-12-p1c-nomes-de-times-e-eventos.md`).

- As partidas da FACEIT são de fila: não há time de verdade, e a demo grava um nome gerado, `team_<nick>`, onde `<nick>` é um jogador do próprio lado (nos 18 times de match_01 a match_09 o nick está no elenco que o site mostra). O site passa a mostrar esse nick, sem o prefixo `team_` (`metrics/times.nome_do_time_faceit`), em vez do primeiro nick em ordem alfabética.
- **Reserva (decisão 28):** o nome ausente, vazio ou genérico (`team`, `CT`, `T`, `Terrorists`, `Counter-Terrorists`, depois de tirar o `team_`) cai em `nome_do_lado_faceit`: o primeiro nick em ordem alfabética, sem caixa (`min` por `casefold`, depois pela ordem do código). Sem nick nenhum, o cabeçalho escreve "Lado A" ou "Lado B".
- **Um lugar só:** tudo lê de `build_web_page._nome_do_lado` (lista de Partidas e landing, cabeçalho, Perfil, Reescrever, cartão do arremesso real da C4, narrativa).
- **Sem arquivo novo:** não há tabela de nomes de time. Os eventos seguem em `data/reference/eventos.json` (decisão 63).
- **Só texto:** nenhum número muda (a impressão dos números fica igual).
