"""
Configuração dos grupos da prancheta (fase 13, item 13.4; decisão 47).

O botão de grupo só aparece no build quando TRÊS coisas são verdade:
  1. GRUPOS_ATIVOS = True (abaixo);
  2. SUPABASE_URL e SUPABASE_ANON_KEY existem (variável de ambiente; no CI, variáveis do repositório no
     GitHub Actions; localmente, o arquivo .env na raiz, que fica fora do git);
  3. o supabase-js fixado em dashboard/web/vendor/ confere com o sha256 gravado ao lado.

A URL do projeto e a chave PÚBLICA (anon ou publishable) são públicas por desenho: quem protege os dados é o
RLS das migrações (supabase/migrations). A chave SECRETA do Supabase nunca entra aqui -- o build recusa uma
chave que tenha cara de secreta, e um teste varre o repositório e o docs/ atrás de qualquer uma.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Começa False e só vira True depois do veredito LIBERADO do agente `seguranca` sobre
# notas/seguranca/grupos.md e da confirmação do Pedro (pedido da fase 13, itens 13.5 e 13.7).
GRUPOS_ATIVOS = False

# Página aberta como arquivo (file://): sem o projeto real não deu para conferir o login anônimo e o Realtime
# com a origem nula do arquivo, então o botão mostra "Grupos funcionam no site publicado" com o link. A parte B
# (tests/test_grupos_integracao.py) confere; se funcionar, isto vira True (decisão 47).
GRUPOS_NO_ARQUIVO_LOCAL = False

# supabase-js fixado numa versão exata (publicada em 2026-09-25 no npm; baixada uma vez do registro, tarball
# conferido pelo shasum do registro). O arquivo é o build UMD do pacote (dist/umd/supabase.js), licença MIT.
VERSAO_SUPABASE_JS = "2.117.2"
VENDOR = PROJECT_ROOT / "dashboard" / "web" / "vendor"
ARQUIVO_SUPABASE_JS = f"supabase-js-{VERSAO_SUPABASE_JS}.js"
CAMINHO_PUBLICADO = f"vendor/{ARQUIVO_SUPABASE_JS}"   # ao lado das páginas, em docs/


def sha256_esperado() -> str:
    return (VENDOR / (ARQUIVO_SUPABASE_JS + ".sha256")).read_text(encoding="utf-8").split()[0].strip().lower()


def confere_biblioteca(caminho: Path | None = None) -> Path:
    """O supabase-js confere com o sha256 gravado ao lado? Senão o build PARA (nunca publica um arquivo trocado)."""
    caminho = caminho or VENDOR / ARQUIVO_SUPABASE_JS
    real = hashlib.sha256(caminho.read_bytes()).hexdigest()
    if real != sha256_esperado():
        raise SystemExit(f"{caminho.name}: sha256 {real} não confere com o gravado ({sha256_esperado()}). "
                         "Não publique: baixe de novo do registro do npm e confira.")
    return caminho


def le_env(arquivo: Path | None = None) -> dict[str, str]:
    """O .env local (CHAVE=valor por linha; # comenta). Sem arquivo, vazio."""
    arquivo = arquivo or PROJECT_ROOT / ".env"
    if not arquivo.exists():
        return {}
    saida = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        saida[k.strip()] = v.strip().strip('"').strip("'")
    return saida


def papel_do_jwt(chave: str) -> str | None:
    """O `role` de uma chave no formato antigo (JWT), ou None se não for JWT."""
    partes = chave.split(".")
    if len(partes) != 3 or not partes[0].startswith("eyJ"):
        return None
    try:
        corpo = partes[1] + "=" * (-len(partes[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(corpo)).get("role")
    except (ValueError, json.JSONDecodeError):
        return None


def chave_e_publica(chave: str) -> bool:
    """Só a publishable (sb_publishable_...) ou a anon antiga (JWT com role anon) passam."""
    if chave.startswith("sb_publishable_"):
        return True
    return papel_do_jwt(chave) == "anon"


def configuracao(site: str | None, pagina: str, ambiente: dict | None = None, ativos: bool | None = None,
                 arquivo_env: Path | None = None) -> dict | None:
    """A configuração do grupo para uma página da prancheta, ou None (sem botão)."""
    ativos = GRUPOS_ATIVOS if ativos is None else ativos
    if not ativos:
        return None
    amb = dict(le_env(arquivo_env))
    amb.update({k: v for k, v in (os.environ if ambiente is None else ambiente).items()
                if k in ("SUPABASE_URL", "SUPABASE_ANON_KEY") and v})
    url, chave = amb.get("SUPABASE_URL", "").strip(), amb.get("SUPABASE_ANON_KEY", "").strip()
    if not url or not chave:
        return None
    if not url.startswith("https://"):
        raise SystemExit("SUPABASE_URL precisa ser https://<projeto>.supabase.co")
    if not chave_e_publica(chave):
        raise SystemExit("SUPABASE_ANON_KEY não é a chave pública (publishable ou anon). A chave secreta nunca "
                         "vai para o build.")
    confere_biblioteca()
    return {"modo": "supabase", "url": url, "chave": chave, "biblioteca": CAMINHO_PUBLICADO,
            "site": site, "pagina": pagina, "arquivoLocal": GRUPOS_NO_ARQUIVO_LOCAL}
