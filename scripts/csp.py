"""CSP por <meta> (L-6 da revisão de segurança dos grupos, fase 16b).

O GitHub Pages não deixa mandar cabeçalho HTTP, então a Content-Security-Policy vai num
`<meta http-equiv>` no <head> de toda página. Sem CSP, um XSS futuro leria a sessão e o localStorage da origem
`github.io`, que é compartilhada com outros sites do Pedro.

O que a política deixa:
- scripts e estilos inline (as páginas são autocontidas: tokens, CSS e JS dentro do HTML) e do próprio site
  (o supabase-js vendorizado, carregado por script dinâmico só ao abrir um grupo, nunca de CDN);
- as fontes do Google Fonts (a única origem externa do site, decisão 44): CSS em fonts.googleapis.com e os
  arquivos em fonts.gstatic.com;
- imagens do próprio site e `data:` (o favicon e as capturas embutidas);
- `connect-src`: só o próprio site. A página da PRANCHETA, e só ela, soma o host do projeto Supabase (https e
  wss) quando o build tem a configuração do grupo (`scripts/grupos_config.py`); sem configuração ou com
  `GRUPOS_ATIVOS = False`, nenhum host além de `'self'`;
- nada de `<object>`/`<embed>` e nenhum `<base>`.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlsplit

# Só o host do projeto Supabase entra no connect-src: letras, números e hífen, terminando em .supabase.co.
# Qualquer outra coisa faz o build parar.
_HOST_DO_PROJETO = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}\.supabase\.co$")


def hosts_do_projeto(url: str | None) -> list[str]:
    """`https://<proj>.supabase.co` -> ["https://<proj>.supabase.co", "wss://<proj>.supabase.co"] (a API e o
    Realtime). Sem URL, lista vazia. URL que não é do Supabase pára o build: o host vai para a política."""
    if not url:
        return []
    partes = urlsplit(url.strip())
    host = (partes.hostname or "").lower()
    if partes.scheme != "https" or not _HOST_DO_PROJETO.match(host) or partes.port or partes.path not in ("", "/"):
        raise SystemExit("SUPABASE_URL precisa ser https://<projeto>.supabase.co (sem caminho nem porta): "
                         "o host entra na política de segurança (CSP) da prancheta.")
    return [f"https://{host}", f"wss://{host}"]


def politica(hosts_de_conexao: list[str] | None = None) -> str:
    """O texto da política. `hosts_de_conexao`: origens extras de `connect-src` (só a prancheta com grupo)."""
    conexao = " ".join(["'self'"] + list(hosts_de_conexao or []))
    return "; ".join([
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        f"connect-src {conexao}",
        "object-src 'none'",
        "base-uri 'none'",
    ])


def meta_csp(hosts_de_conexao: list[str] | None = None) -> str:
    return f'<meta http-equiv="Content-Security-Policy" content="{html.escape(politica(hosts_de_conexao), quote=True)}">'
