# Decisão 69: A malha de navegação do CS2, só o dado derivado, entra no repositório (PC1)

- **ID:** 69
- **Status:** vigente
- **Data:** 2026-11-15
- **Resumo:** O site pode usar os polígonos e as ligações das áreas de navegação do CS2 (os arquivos `.nav` da Valve), derivados num arquivo por mapa, com as mesmas regras dos radares: uso não comercial,
  crédito à Valve, nenhuma marca da Valve, e o `.nav` original nunca entra no repositório.

## Texto

69. **A malha do jogo, derivada** (PC1; decisão do Pedro em 2026-11-15, depois de a PC0 mostrar que só ela cobre os 10 mapas e os andares).

- **O que entra:** `data/caminhos/malha/<mapa>.json` (`scripts/gera_malha.py`): os polígonos das áreas (cantos inteiros) e as ligações dirigidas entre elas (as escadas de mão ligadas nos dois sentidos), com a versão do
  `.nav` de origem, o sha256 dele, a versão do awpy que o leu e a data. O crédito vai no próprio arquivo: "Derivado dos arquivos de navegação do CS2, da Valve (uso não comercial); o projeto não tem ligação com a Valve."
- **O que NUNCA entra:** o `.nav` original (nem copiado, nem em `data/interim`, nem em `docs/`); `tests/test_caminhos.py` falha se houver um `*.nav` no repositório. Nenhuma marca, logotipo ou nome comercial da Valve
  além da atribuição.
- **Como se gera:** a malha vem da instalação do CS2 no PC do Pedro (o `.nav` está dentro do `.vpk` de cada mapa) e é lida com o awpy 3.3.0 num venv à parte (o awpy do projeto, 2.0.2, só lê a versão 30 a 35
  e o jogo grava a 36); o projeto NÃO muda de awpy. O CI não tem o jogo: **o build e o CI só leem o arquivo derivado.** Passo a passo em `notas/caminhos-como-recriar-a-malha.md`.
- **Atualização do jogo:** `scripts/gera_malha.py --confere` diz, por mapa, se o `.nav` mudou (versão, sha256, áreas e ligações); o arquivo novo entra num commit à parte, com a diferença no texto.
- **Crédito no site:** o arquivo derivado carrega o crédito; a linha do rodapé ("os caminhos das peças derivam dos arquivos de navegação do CS2, da Valve") entra junto com o primeiro uso na tela (PC2), porque a
  PC1 não muda nada na tela.
