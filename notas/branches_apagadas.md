# Branches apagadas

Cartão 8 (fase 17): apagar as branches já mescladas no `main`, locais e do GitHub, menos a `fase-6-decisivo`.
Cada uma foi conferida de novo no momento de apagar (`git merge-base --is-ancestor <hash> main`); se tivesse
deixado de ser ancestral do `main`, não seria apagada. As tags (`baseline-*`) não foram tocadas. Ficaram também
o `main`, as branches em uso em worktrees no dia (`fase-17-cartoes-2-3-4`, `fase-18b-calibracao`) e as
branches do Dependabot no GitHub, que não estão mescladas (PRs abertos).

Data: 2026-10-16.

| branch | onde | hash (último commit) |
|---|---|---|
| `design-0-entrega` | local | `f36715e9b43fc519461d5679ef93b16b83e181a8` |
| `design-a-tokens` | local | `c2ad53853441d1c4550fcba0659a3aa843438fef` |
| `design-b1-cabecalho` | local | `3825fed03b2b0f44b8a78349807eb680c623de2a` |
| `design-b2-replay` | local | `8cebe6926e99e28307aca31f8b92212db3d26a2d` |
| `design-b2b-radar` | local | `535ac2e8cecd1840e6d37cbb96b4353dbc6bac96` |
| `design-b3-resumo-jogadores` | local | `975452cf5518372fffbdc663162f44342b948a3e` |
| `design-c-landing` | local | `62baa012d2cbac6345c02513142d070482c768aa` |
| `design-d-jogadores` | local | `acac674b28fa33501cfe6a36b93d7830c6c4f74c` |
| `design-e-prancheta` | local | `14ff39331d4b16af5522a4a4791c7be4a88ac738` |
| `design-e2-prancheta` | local | `2a9c4cde7d4fba378adaabdebe65834d6390c18e` |
| `design-e3-acessibilidade` | local | `2ceebab16ff1e2b135cfa380251647c0c96b37ea` |
| `fase-1-correcoes` | local | `95c18700d1fb5a8ef3f7d1544739ec474c60c877` |
| `fase-11-granadas-no-desenho` | local | `dacf70711f0e2e3952eef6217aec76685d454f47` |
| `fase-12-perfil-erros` | local | `8706c7182171cd46249210f0f008f011f9179284` |
| `fase-12b-ajustes` | local | `ed29d5083e824380ac1c8f9078a4871a2d9482ae` |
| `fase-12b-grupo` | local | `09b7f606345db6cfc2cfc1892be6cf6243db929f` |
| `fase-12b-perfil` | local | `af54c3d9d90536fc828b525feb8d1a2e3ba02106` |
| `fase-13-grupos` | local | `968b894fec6ae2c56a9b078e913b3ac781f36502` |
| `fase-14-claude-md` | local | `f0a9e9f72849a447ed25f691b7f9b8c752bda01f` |
| `fase-15-componentes` | local | `db74960eb323be583bc820b9f94844431b18ce25` |
| `fase-15-granada` | local | `ea856c599361c042b1c34a0682316a86378e7eba` |
| `fase-15-grupo` | local | `30fba43086932348b510a71a6206785223a5105d` |
| `fase-15-perfil` | local | `1c4aba429310cb9a8c117d6435216b3ae5fd6bb5` |
| `fase-16a-pendencias-15` | local | `396c94ea9c8dd5b6fa9d9ea20efc18161bc8250b` |
| `fase-16b-cliente` | local | `49bfbcdb6720205739c328d41c0b87a7bdbf197f` |
| `fase-16b-seguranca` | local | `ed1a55ff66459294b3be94b4ef178fb9c5beb6d4` |
| `fase-16b-servidor` | local | `712f15ead79adc22380fdeae973cc450a1b1faeb` |
| `fase-17-contador-de-operacoes` | local | `40cf7134ae36d2b4f84b2c41d31ac653ee03bdb9` |
| `fase-17-galil-famas` | local | `f31945f2bdab6d2acc2e4e087914d07d54b18aa6` |
| `fase-17-nvda-e-95` | local | `ae296528994ff18da1a474e76c4eda12603cf58e` |
| `fase-17-ponto-atrasado` | local | `bd33fa47eb0b84da96cd9313d71a06793aaa6f83` |
| `fase-17-sem-modo-desligado` | local | `52805fb91ce6efb517113934c19bb2afca5c5e8f` |
| `fase-17a-ajustes` | local | `e4247409bbf7817a0df8d4601bcfe471fe331320` |
| `fase-17a-copias` | local | `b4d4cebd4ca456835483cd9f6f5269f59e9dadd3` |
| `fase-17a-material` | local | `989e4e5226aa2aad303450e3e321844526c2b414` |
| `fase-18-claude-md` | local | `36a2426e9059fdd37f7a8b3097b3c41cb9f9cc5e` |
| `fase-18-erros-revisao` | local | `5b059dc8191c91c2a8bbb4b5ecabf39287850e5b` |
| `fase-2-vitrine` | local | `c27b9353de4414930defcf009ceea3303fc34e04` |
| `fase-3-claude-md` | local | `cc4ce459079937401793fc5bb41538bf020bcbea` |
| `fase-4-rigor` | local | `f944da2c989eb90adfc5c0f9849c2ef8c62a8ee9` |
| `fase-5-acabamento` | local | `0e13ea9c9371c2dadfd092a0f118883e462689f4` |
| `fase-7-metricas` | local | `8ac5519872618961c5b510bb3db7fb768ed1832b` |
| `fase-8-prancheta-tempo` | local | `0bc43b37bd0239d568af7c0341390e85ccedf1a0` |
| `fase-8a-clique` | local | `0bb7c9fd02c15e4e0f54facfd2d44c43c05d34dc` |
| `fase-9-round-na-prancheta` | local | `fbf63ffc069d80ef08b6858a3f88bf35260dc62f` |
| `investigacao-faceit` | local | `7adc84f5e65f8e64e5bb0b67d90297c672c8b1b5` |
| `pendencias-para-o-pedro` | local | `be8b237b65e98ad62ed3127ad7ad70fe0aa84a6b` |
| `prancheta-fluida` | local | `7de4f46b8323876bb09b1ca9c2196b20e51ac19e` |
| `rota-a-em-andamento` | local | `068c578c9fa59dd5641d00b1fd5eae35f51d6209` |
| `rota-b` | local | `53d9bf846d090400254a6e47587c5a19d57e0dab` |
| `worktree-agent-a19ea2c3e37a0ade2` | local | `190a0f0eb7967779e3ec3b3bd66f8c5d3eab8916` |
| `worktree-agent-a1f2fd7ff6e6d6fa7` | local | `fde69b141551553493d907a2c063c49e5cf3feac` |
| `worktree-agent-a86f36c803bb8064e` | local | `653f5c3a1856c0a4cfea9738d88af36fad2f3854` |
| `worktree-agent-a8e21ba4206b755a1` | local | `653f5c3a1856c0a4cfea9738d88af36fad2f3854` |
| `worktree-agent-a97f81b9e74388aad` | local | `fde69b141551553493d907a2c063c49e5cf3feac` |
| `worktree-agent-acd3e4bd427bc3263` | local | `190a0f0eb7967779e3ec3b3bd66f8c5d3eab8916` |
| `worktree-agent-ae54065a4ba488bcd` | local | `653f5c3a1856c0a4cfea9738d88af36fad2f3854` |
| `design-0-entrega` | GitHub | `f36715e9b43fc519461d5679ef93b16b83e181a8` |
| `design-a-tokens` | GitHub | `c2ad53853441d1c4550fcba0659a3aa843438fef` |
| `design-b1-cabecalho` | GitHub | `3825fed03b2b0f44b8a78349807eb680c623de2a` |
| `design-b2-replay` | GitHub | `8cebe6926e99e28307aca31f8b92212db3d26a2d` |
| `design-b2b-radar` | GitHub | `535ac2e8cecd1840e6d37cbb96b4353dbc6bac96` |
| `design-b3-resumo-jogadores` | GitHub | `975452cf5518372fffbdc663162f44342b948a3e` |
| `design-c-landing` | GitHub | `62baa012d2cbac6345c02513142d070482c768aa` |
| `design-d-jogadores` | GitHub | `acac674b28fa33501cfe6a36b93d7830c6c4f74c` |
| `design-e-prancheta` | GitHub | `14ff39331d4b16af5522a4a4791c7be4a88ac738` |
| `design-e2-prancheta` | GitHub | `2a9c4cde7d4fba378adaabdebe65834d6390c18e` |
| `design-e3-acessibilidade` | GitHub | `2ceebab16ff1e2b135cfa380251647c0c96b37ea` |
| `fase-1-correcoes` | GitHub | `95c18700d1fb5a8ef3f7d1544739ec474c60c877` |
| `fase-2-vitrine` | GitHub | `c27b9353de4414930defcf009ceea3303fc34e04` |
| `fase-3-claude-md` | GitHub | `cc4ce459079937401793fc5bb41538bf020bcbea` |
| `fase-4-rigor` | GitHub | `f944da2c989eb90adfc5c0f9849c2ef8c62a8ee9` |
| `fase-5-acabamento` | GitHub | `0e13ea9c9371c2dadfd092a0f118883e462689f4` |
| `fase-7-metricas` | GitHub | `8ac5519872618961c5b510bb3db7fb768ed1832b` |
| `fase-8-prancheta-tempo` | GitHub | `0bc43b37bd0239d568af7c0341390e85ccedf1a0` |
| `fase-8a-clique` | GitHub | `0bb7c9fd02c15e4e0f54facfd2d44c43c05d34dc` |
| `fase-9-round-na-prancheta` | GitHub | `fbf63ffc069d80ef08b6858a3f88bf35260dc62f` |
| `investigacao-faceit` | GitHub | `7adc84f5e65f8e64e5bb0b67d90297c672c8b1b5` |
| `pendencias-para-o-pedro` | GitHub | `be8b237b65e98ad62ed3127ad7ad70fe0aa84a6b` |
| `prancheta-fluida` | GitHub | `7de4f46b8323876bb09b1ca9c2196b20e51ac19e` |
| `rota-a-em-andamento` | GitHub | `068c578c9fa59dd5641d00b1fd5eae35f51d6209` |
| `rota-b` | GitHub | `53d9bf846d090400254a6e47587c5a19d57e0dab` |
