"""Grupos na prancheta (fase 13, itens 13.4 e 13.6, parte A, 6 a 8): configuração, chaves e "sem grupo, nada muda".

- Sem URL e chave, ou com GRUPOS_ATIVOS = False, o botão não aparece e a página é a de sempre.
- Sem grupo aberto, a prancheta não faz pedido de rede nenhum além dos de sempre (Playwright registrando) e o
  supabase-js não entra na página: ele é carregado por script dinâmico só ao criar ou entrar num grupo.
- O supabase-js fixado confere com o sha256 gravado ao lado.
- A chave secreta do Supabase (a do papel de serviço) não aparece no repositório nem no docs/.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import re
import subprocess
import threading
from functools import partial
from pathlib import Path

import pytest

from scripts import grupos_config as gc

RAIZ = Path(__file__).resolve().parents[1]
MAPA = "de_mirage"
URL_FALSA = "https://exemplo-sem-projeto.supabase.co"
CHAVE_FALSA = "sb_publishable_teste0000000000000000"
# a palavra proibida é montada aqui para este arquivo não ser ele mesmo uma ocorrência
PAPEL_PROIBIDO = "service" + "_role"


def _jwt(papel: str) -> str:
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return b({"alg": "HS256", "typ": "JWT"}) + "." + b({"role": papel, "iss": "supabase"}) + ".assinatura"


# --- 13.4: a configuração ----------------------------------------------------------

def test_grupos_comecam_desligados():
    assert gc.GRUPOS_ATIVOS is False
    assert gc.configuracao("https://x/", "p.html", ambiente={"SUPABASE_URL": URL_FALSA, "SUPABASE_ANON_KEY": CHAVE_FALSA}) is None


def test_sem_url_ou_chave_nao_ha_grupo(tmp_path):
    vazio = tmp_path / ".env"
    assert gc.configuracao("s", "p", ambiente={}, ativos=True, arquivo_env=vazio) is None
    assert gc.configuracao("s", "p", ambiente={"SUPABASE_URL": URL_FALSA}, ativos=True, arquivo_env=vazio) is None
    assert gc.configuracao("s", "p", ambiente={"SUPABASE_ANON_KEY": CHAVE_FALSA}, ativos=True, arquivo_env=vazio) is None
    c = gc.configuracao("s", "p", ambiente={"SUPABASE_URL": URL_FALSA, "SUPABASE_ANON_KEY": CHAVE_FALSA}, ativos=True,
                        arquivo_env=vazio)
    assert c["modo"] == "supabase" and c["biblioteca"] == "vendor/supabase-js-2.117.2.js" and c["arquivoLocal"] is False


def test_o_env_local_vale_e_o_ambiente_tem_precedencia(tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"# local\nSUPABASE_URL={URL_FALSA}\nSUPABASE_ANON_KEY=\"{CHAVE_FALSA}\"\n", encoding="utf-8")
    c = gc.configuracao("s", "p", ambiente={}, ativos=True, arquivo_env=env)
    assert c["url"] == URL_FALSA and c["chave"] == CHAVE_FALSA
    outra = "https://outro.supabase.co"
    assert gc.configuracao("s", "p", ambiente={"SUPABASE_URL": outra}, ativos=True, arquivo_env=env)["url"] == outra


def test_o_build_recusa_chave_que_nao_e_publica(tmp_path):
    env = tmp_path / ".env"
    for chave in ("sb_secret_" + "x" * 30, _jwt(PAPEL_PROIBIDO)):
        with pytest.raises(SystemExit):
            gc.configuracao("s", "p", ambiente={"SUPABASE_URL": URL_FALSA, "SUPABASE_ANON_KEY": chave}, ativos=True,
                            arquivo_env=env)
    assert gc.chave_e_publica(_jwt("anon")) and gc.chave_e_publica(CHAVE_FALSA)


def test_env_e_node_modules_fora_do_git():
    ignorado = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=RAIZ).returncode == 0
    assert ignorado
    assert subprocess.run(["git", "check-ignore", "-q", "supabase/tests/node_modules/x"], cwd=RAIZ).returncode == 0


# --- o supabase-js fixado -------------------------------------------------------------

def test_supabase_js_confere_com_o_sha256_gravado(tmp_path):
    arquivo = gc.confere_biblioteca()
    assert hashlib.sha256(arquivo.read_bytes()).hexdigest() == gc.sha256_esperado()
    assert re.fullmatch(r"[0-9a-f]{64}", gc.sha256_esperado())
    trocado = tmp_path / gc.ARQUIVO_SUPABASE_JS
    trocado.write_bytes(arquivo.read_bytes() + b"\n// mexido")
    with pytest.raises(SystemExit):
        gc.confere_biblioteca(trocado)


def test_licenca_do_supabase_js_no_readme_e_ao_lado():
    assert (gc.VENDOR / "supabase-js-LICENSE.txt").read_text(encoding="utf-8").startswith("MIT License")
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert "supabase-js" in readme and gc.VERSAO_SUPABASE_JS in readme and "MIT" in readme


# --- 13.6.8: nenhuma chave secreta no repositório nem no docs/ ---------------------

def _arquivos_de_texto():
    versionados = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=RAIZ, capture_output=True,
                                 text=True, encoding="utf-8").stdout.splitlines()
    caminhos = [RAIZ / f for f in versionados]
    docs = RAIZ / "docs"
    if docs.exists():
        caminhos += [p for p in docs.rglob("*") if p.is_file()]
    for p in caminhos:
        if not p.is_file() or p.suffix.lower() in (".png", ".webp", ".gz", ".parquet", ".jpg", ".ico", ".woff2"):
            continue
        if p.stat().st_size > 30 * 1024 * 1024:
            continue
        try:
            yield p, p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue


def test_nenhuma_chave_secreta_no_repositorio_nem_no_docs():
    jwt = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.(eyJ[A-Za-z0-9_-]{8,})\.[A-Za-z0-9_-]{8,}")
    achados = []
    for p, texto in _arquivos_de_texto():
        if PAPEL_PROIBIDO in texto:
            achados.append(f"{p.relative_to(RAIZ)}: a palavra do papel de serviço")
        if re.search(r"sb_secret_[A-Za-z0-9_-]{8,}", texto):
            achados.append(f"{p.relative_to(RAIZ)}: chave sb_secret_")
        for m in jwt.finditer(texto):
            if gc.papel_do_jwt(m.group(0)) not in (None, "anon"):
                achados.append(f"{p.relative_to(RAIZ)}: JWT com papel {gc.papel_do_jwt(m.group(0))}")
    assert achados == []


# --- 13.6.6 e 13.6.7: sem grupo, nada muda --------------------------------------------

def test_sem_configuracao_a_pagina_e_a_de_sempre():
    from scripts.build_tactics_page import build_html
    sem = build_html(MAPA)
    assert "Grupo.prepara" not in sem and "var Sala =" not in sem and "<!--__GRUPO__-->" not in sem
    assert 'data-aba="grupo"' not in sem
    assert build_html(MAPA, grupo=None) == sem


def test_o_build_do_site_sem_grupo_nao_publica_o_supabase_js():
    texto = (RAIZ / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert "confere_biblioteca()" in texto and "if com_grupo:" in texto


sync_api = pytest.importorskip("playwright.sync_api")
from tests.test_tactics_browser import navegador  # noqa: E402,F401


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def site_local(tmp_path_factory):
    """Duas pranchetas servidas por http (como no Pages): uma sem grupo e uma com o grupo configurado (URL e chave
    falsas), com o supabase-js em vendor/ ao lado, como o build_site publica."""
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    raiz = tmp_path_factory.mktemp("site")
    (raiz / "sem").mkdir()
    (raiz / "com" / "vendor").mkdir(parents=True)
    pagina = arquivo_da_pagina(MAPA)
    (raiz / "sem" / pagina).write_text(build_html(MAPA), encoding="utf-8")
    cfg = gc.configuracao("http://127.0.0.1/", pagina, ambiente={"SUPABASE_URL": URL_FALSA, "SUPABASE_ANON_KEY": CHAVE_FALSA},
                          ativos=True, arquivo_env=raiz / ".env")
    (raiz / "com" / pagina).write_text(build_html(MAPA, grupo=cfg), encoding="utf-8")
    (raiz / "com" / "vendor" / gc.ARQUIVO_SUPABASE_JS).write_bytes(gc.confere_biblioteca().read_bytes())
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(_Silencioso, directory=str(raiz)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield {"url": f"http://127.0.0.1:{srv.server_address[1]}", "pagina": pagina, "raiz": raiz, "cfg": cfg}
    srv.shutdown()


def _abre_registrando(navegador, url):
    ctx = navegador.new_context(viewport={"width": 1300, "height": 950})
    pg = ctx.new_page()
    pedidos, erros = [], []
    pg.on("request", lambda r: pedidos.append(r.url))
    pg.on("pageerror", lambda e: erros.append(str(e)))
    # o Supabase de mentira não existe: qualquer pedido a ele falha como "fora do ar"
    pg.route(re.compile(r".*supabase\.co.*"), lambda rota: rota.abort())
    pg.goto(url)
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.wait_for_timeout(300)
    return ctx, pg, pedidos, erros


def _locais(pedidos, base):
    return sorted(p.replace(base + "/com/", "/").replace(base + "/sem/", "/") for p in pedidos)


def test_sem_grupo_aberto_nenhum_pedido_de_rede_a_mais_e_o_supabase_js_fica_fora(navegador, site_local):
    base, pagina = site_local["url"], site_local["pagina"]
    ctx1, sem, pedidos_sem, erros_sem = _abre_registrando(navegador, f"{base}/sem/{pagina}")
    ctx2, com, pedidos_com, erros_com = _abre_registrando(navegador, f"{base}/com/{pagina}")
    try:
        assert not erros_sem and not erros_com
        # o botão não aparece sem configuração; aparece com ela
        assert sem.locator("#pr-aba-grupo").count() == 0
        assert com.locator("#pr-aba-grupo").count() == 1
        # mexer na prancheta e abrir a aba Grupo não faz pedido nenhum
        com.click("#pr-aba-grupo")
        com.fill("#gr-nick", "nomad")
        com.wait_for_timeout(200)
        assert _locais(pedidos_com, base) == _locais(pedidos_sem, base)
        assert not any("supabase" in p for p in pedidos_com)
        # peso: a página com grupo leva só sala.js, grupo.js e o CSS da aba; o supabase-js não está nela
        html_sem = (site_local["raiz"] / "sem" / pagina).read_bytes()
        html_com = (site_local["raiz"] / "com" / pagina).read_bytes()
        js_supabase = gc.confere_biblioteca().read_bytes()
        assert js_supabase[:2000] not in html_com
        extra = len(html_com) - len(html_sem)
        partes = sum((RAIZ / "dashboard" / "web" / f).stat().st_size for f in ("sala.js", "grupo.js", "grupo.css"))
        assert 0 < extra <= partes + 2048, (extra, partes)
    finally:
        ctx1.close(); ctx2.close()


def test_criar_grupo_carrega_o_supabase_js_so_na_hora_e_fora_do_ar_avisa(navegador, site_local):
    base, pagina = site_local["url"], site_local["pagina"]
    ctx, pg, pedidos, erros = _abre_registrando(navegador, f"{base}/com/{pagina}")
    try:
        assert not any("vendor/" in p for p in pedidos)
        pg.click("#pr-aba-grupo")
        pg.fill("#gr-nick", "nomad")
        pg.click('[data-acao="criar"]')
        pg.wait_for_selector("#gr-erro")
        assert pg.inner_text("#gr-erro") == "✕ Erro: Grupo indisponível agora. A tática continua salva neste navegador."
        assert any(p.endswith("vendor/" + gc.ARQUIVO_SUPABASE_JS) for p in pedidos)
        assert any("supabase.co" in p for p in pedidos)          # tentou o login anônimo (e o servidor "caiu")
        assert pg.evaluate("() => typeof window.supabase.createClient") == "function"
        # a prancheta segue funcionando sozinha
        assert pg.evaluate("() => Grupo._interno.G().fase") == "fora"
        assert not erros
    finally:
        ctx.close()


def test_aberta_como_arquivo_o_grupo_manda_para_o_site_publicado(navegador, site_local):
    ctx = navegador.new_context()
    pg = ctx.new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(r.url))
    try:
        pg.goto((site_local["raiz"] / "com" / site_local["pagina"]).as_uri())
        pg.wait_for_function("() => !!document.getElementById('pr-painel-grupo')")
        pg.click("#pr-aba-grupo")
        texto = pg.inner_text("#pr-painel-grupo")
        assert "Grupos funcionam no site publicado." in texto
        assert pg.get_attribute("#pr-painel-grupo a", "href") == "http://127.0.0.1/" + site_local["pagina"]
        assert pg.locator('[data-acao="criar"]').count() == 0
        assert not any("supabase" in p or "vendor/" in p for p in pedidos)
    finally:
        ctx.close()
