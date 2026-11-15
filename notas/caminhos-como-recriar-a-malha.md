# Como recriar a malha derivada do CS2 (`data/caminhos/malha/`)

Decisão 69. O `.nav` da Valve nunca entra no repositório; só o dado derivado. O CI não tem o jogo: ele só lê os arquivos já derivados. Quem tem o CS2 instalado (o PC do Pedro) recria assim:

1. **Um venv à parte** (o awpy do projeto, 2.0.2, NÃO muda; ele só lê `.nav` de versão 30 a 35 e o jogo grava a 36):
   ```
   py -3.12 -m venv %TEMP%\awpy3-venv
   %TEMP%\awpy3-venv\Scripts\python.exe -m pip install awpy==3.3.0 vpk==1.4.0
   ```
2. **Gerar** (de dentro da pasta do projeto; o padrão é a pasta da Steam `C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive`, ou `--cs2 CAMINHO`):
   ```
   %TEMP%\awpy3-venv\Scripts\python.exe -m scripts.gera_malha            # os 10 mapas
   %TEMP%\awpy3-venv\Scripts\python.exe -m scripts.gera_malha --mapas de_mirage de_nuke
   ```
3. **Depois de uma atualização do jogo**, antes de gerar: `... -m scripts.gera_malha --confere` mostra, por mapa, se o `.nav` mudou (versão, sha256, número de áreas e ligações). O arquivo novo entra num
   commit à parte, com essa diferença na mensagem.
4. **Remontar o grafo** (precisa do `data/interim`, para o corpus): `py -3.12 -m scripts.build_caminhos` (todos) ou `... de_mirage`; o site (`scripts.build_site`) só lê `data/caminhos/*.json`.
