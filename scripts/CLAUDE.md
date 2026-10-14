# scripts/: referências, calibração, biblioteca e build

Complementa o `CLAUDE.md` da raiz e não o substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. Antes de mexer num `fit_*` leia também o `CLAUDE.md` da pasta da métrica:
`fit_global_clusters` → `clustering/`; `fit_archetype_reference`, `fit_rating`, `fit_economia`,
`fit_perfil_reference` e `fit_erros_reference` → `metrics/`.

## Dados

- `clean_match.limpa` recusa apagar sem uma cópia de mesmo sha256 nas pastas irmãs
  "<projeto> - BACKUP*", lida NA HORA dos dois lados (lista gravada não vale), mesmo chamada pelo
  Python com `confirmar=True`; sem `confirmar`, só lista arquivo, tamanho, cópia e hash (36)
- Escala dos papéis: reajuste com `fit_archetype_reference` sempre que processar demo nova ou mexer
  num componente (16); economia: refazer `economia_reference.json` a cada demo nova, e a tabela
  regerada tem de dar exatamente o arquivo gravado (8i). O `reprocessa` não faz isso por padrão:
  reajustar é decisão (28)

## Rating

- Calibração só com partidas oficiais cobertas pela HLTV, nunca FACEIT; mínimo de 7 de treino + 3
  de teste, divisão por PARTIDA e nunca por jogador (22c)
- `componentes_do_corpus` recebe a referência: os pesos são ajustados na mesma escala em que o site
  os usa (22l)
- Refazer a referência de escala exige refazer os pesos (`fit_rating --fit-pesos`); o rating marca
  `pesos_desatualizados` (22l)

## Biblioteca, lugares e build

- `data/lineups/` é gerada LOCALMENTE por `scripts.build_lineups` (depende do interim, que não vai
  ao git nem ao CI); só entra arremesso com reprodução exata; regerar depois de mudar
  `metrics/grenade_throws.py` (32)
- Nome de lugar só do campo `place` dos ticks, em inglês como o jogo escreve (sem tradução); célula
  sem tick não tem nome; o mapa só ganha tabela com `MIN_PARTIDAS` (2) e `MIN_ACERTO` (93%) fora da
  amostra, e abaixo disso a tela fica sem nome (42)
- JSON dentro de `<script>` só por `scripts/json_em_script.py` (37)
- `cluster_names.json` entra no payload do site (8)
- Do build saem prontos o cabeçalho da partida (placar, "venceu", "começou CT/TR") e o `<title>`
  único (o evento entra quando dois títulos se repetiriam) (44)
- supabase-js entra em versão exata, com o sha256 conferido pelo build, e só é carregado ao criar ou
  entrar num grupo; sem `GRUPOS_ATIVOS`, URL e chave pública, a página é byte a byte a do build sem
  grupo (47)
