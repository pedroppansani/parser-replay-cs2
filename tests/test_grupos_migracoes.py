"""Grupos na prancheta (fase 13, item 13.1): as migrações do Supabase, lidas como texto.

O que se confere aqui é o que não pode escapar numa edição futura das migrações: RLS ligado em toda tabela,
nenhuma política que libera tudo, toda função `security definer` com `search_path` fixo, o log imutável (sem
grant de update/delete em operacoes) e os limites com os mesmos números do cliente e do documento de
segurança. As políticas rodam de verdade em `supabase/tests/politicas_no_pglite.mjs` (Postgres 17 em WASM):
o teste no fim chama esse script quando o Node e o PGlite estão instalados, e pula com o motivo quando não.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MIGRACOES = RAIZ / "supabase" / "migrations"


def _sql() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(MIGRACOES.glob("*.sql")))


def test_migracoes_numeradas_em_ordem():
    nomes = sorted(p.name for p in MIGRACOES.glob("*.sql"))
    assert len(nomes) == 7   # 1 a 5 da fase 13; 6 e 7 da fase 16b (tetos de uso, L-1, L-2, L-3, L-5)
    assert all(re.match(r"^\d{14}_grupos_[a-z_]+\.sql$", n) for n in nomes), nomes


def test_rls_ligado_em_toda_tabela_criada():
    sql = _sql()
    tabelas = re.findall(r"create table (\w+\.\w+)", sql)
    assert set(tabelas) == {"public.salas", "public.membros", "public.operacoes", "grupos.tentativas", "grupos.expulsos",
                       "grupos.chamadas"}
    for t in tabelas:
        assert re.search(rf"alter table {re.escape(t)}\s+enable row level security", sql), t


def test_nenhuma_politica_libera_tudo():
    sql = _sql()
    assert not re.search(r"using\s*\(\s*true\s*\)", sql, re.I)
    assert not re.search(r"with check\s*\(\s*true\s*\)", sql, re.I)
    assert not re.search(r"\bto\s+anon\b", sql.split("revoke")[0])   # nenhuma política para quem não fez login


def test_security_definer_sempre_com_search_path_fixo():
    sql = _sql()
    funcoes = re.findall(r"create or replace function (\S+)\((.*?)\$\$", sql, re.S)
    assert funcoes
    for nome, corpo in funcoes:
        if "security definer" in corpo:
            assert "set search_path = ''" in corpo, nome


def test_log_imutavel_sem_update_nem_delete_em_operacoes():
    sql = _sql()
    assert not re.search(r"grant [^;]*\b(update|delete)\b[^;]* on public\.operacoes", sql)
    assert not re.search(r"create policy \w+ on public\.operacoes\s+for (update|delete)", sql)


def test_entrar_na_sala_e_a_unica_porta_de_membros():
    sql = _sql()
    assert not re.search(r"grant [^;]*\binsert\b[^;]* on public\.membros", sql)
    assert not re.search(r"create policy \w+ on public\.membros\s+for insert", sql)
    assert "create or replace function public.entrar_na_sala(p_codigo text, p_nick text)" in sql


def test_limites_iguais_no_banco_no_cliente_e_no_documento():
    """10 membros, 20 operações por segundo, 8 KB, 30 dias e 5 erros de código: o mesmo número nos três."""
    sql = _sql()
    sala_js = (RAIZ / "dashboard" / "web" / "sala.js").read_text(encoding="utf-8")
    doc = (RAIZ / "notas" / "seguranca" / "grupos.md").read_text(encoding="utf-8")
    assert "c_max_membros constant int := 10" in sql and "MAX_MEMBROS = 10" in sala_js
    assert "c_max_ops_por_segundo constant int := 20" in sql and "MAX_OPS_POR_SEGUNDO = 20" in sala_js
    assert "octet_length(op::text) <= 8192" in sql and "MAX_BYTES_DA_OPERACAO = 8192" in sala_js
    assert "interval '30 days'" in sql
    assert "c_max_erros_de_codigo constant int := 5" in sql
    for frase in ("10 membros", "20 operações por segundo", "8 KB", "30 dias", "5 códigos errados"):
        assert frase in doc, frase


def test_o_documento_de_seguranca_traz_o_sql_que_roda():
    """notas/seguranca/grupos.md (13.7) tem o SQL inteiro das políticas e da função entrar_na_sala, igual às migrações."""
    doc = (RAIZ / "notas" / "seguranca" / "grupos.md").read_text(encoding="utf-8")
    politicas = (MIGRACOES / "20261013000002_grupos_politicas.sql").read_text(encoding="utf-8").strip()
    assert politicas in doc
    funcoes = (MIGRACOES / "20261013000003_grupos_funcoes.sql").read_text(encoding="utf-8")
    i = funcoes.index("create or replace function public.entrar_na_sala")
    j = funcoes.index("grant execute on function public.entrar_na_sala(text, text) to authenticated;", i)
    assert funcoes[i:j] in doc
    for p in re.findall(r"create policy (\w+)", _sql()):
        assert f"create policy {p}" in doc, p


def test_politicas_rodam_num_postgres_de_verdade():
    """O script do PGlite (Postgres 17 em WASM) aplica as migrações e confere cada política (parte B, em local)."""
    node = shutil.which("node")
    script = RAIZ / "supabase" / "tests" / "politicas_no_pglite.mjs"
    if not node or not (RAIZ / "supabase" / "tests" / "node_modules" / "@electric-sql" / "pglite").exists():
        pytest.skip("sem Node ou sem o PGlite (npm install --prefix supabase/tests @electric-sql/pglite@0.3.7)")
    saida = subprocess.run([node, str(script), str(RAIZ)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
    linhas = [l for l in saida.stdout.splitlines() if l.startswith(("ok", "FALHOU", "OK", "FALHA"))]
    assert "TUDO OK" in saida.stdout, "\n".join(linhas)
    assert sum(l.startswith("ok") for l in linhas) >= 120


# --- fase 16b: tetos de uso, tipos permitidos e o SQL novo no documento --------------------------------------------

def _funcao(nome: str) -> str:
    """O corpo da ÚLTIMA definição de uma função nas migrações (a 7 troca as da 3)."""
    sql = _sql()
    achados = [m.start() for m in re.finditer(rf"create or replace function {re.escape(nome)}\(", sql)]
    assert achados, nome
    i = achados[-1]
    return sql[i:sql.index("$$;", sql.index("$$", i) + 2) + 3]


def test_a_lista_de_tipos_do_servidor_e_a_do_javascript_e_a_do_python():
    """L-3: a lista de tipos de operação do SQL, a de OPERACOES em tactics.js e a de metrics/tactics.py são a mesma.
    Operação nova da prancheta exige migração nova que troque grupos.tipos_de_operacao()."""
    from metrics.tactics import OPERACOES

    corpo = _funcao("grupos.tipos_de_operacao")
    no_sql = re.findall(r"'([a-z_]+)'", corpo[corpo.index("array["):corpo.index("]::text[]")])
    js = (RAIZ / "dashboard" / "web" / "tactics.js").read_text(encoding="utf-8")
    inicio = js.index("var OPERACOES = {")
    bloco = js[inicio:js.index("};", inicio)]
    bloco = " ".join(l for l in bloco.splitlines() if not l.strip().startswith("//"))
    no_js = re.findall(r"(\w+):\s*\[", bloco)
    assert len(no_sql) == len(set(no_sql)) == len(OPERACOES) == 26
    assert set(no_sql) == set(no_js) == set(OPERACOES)


def test_os_tetos_vem_da_medicao_do_maior_round_real():
    """B-2: o teto por sala é o maior entre 5.000 operações / 2 MB e 4x o maior round real (scripts/mede_round_na_prancheta.py)."""
    import json

    medicao = json.loads((RAIZ / "supabase" / "medicao" / "maior_round_na_prancheta.json").read_text(encoding="utf-8"))
    assert medicao["rounds"] >= 1000
    ops = max(medicao["maior_em_operacoes"]["ops"], medicao["maior_em_bytes"]["ops"])
    bytes_ = max(medicao["maior_em_operacoes"]["bytes"], medicao["maior_em_bytes"]["bytes"])
    sql = _sql()
    teto_ops = max(5000, 4 * ops)
    teto_bytes = max(2 * 1024 * 1024, 4 * bytes_)
    assert f"c_max_ops_por_sala constant int := {teto_ops}" in sql
    assert f"c_max_bytes_por_sala constant bigint := {teto_bytes}" in sql


def test_os_tetos_novos_tem_o_mesmo_numero_no_banco_no_cliente_e_no_documento():
    sql = _sql()
    sala_js = (RAIZ / "dashboard" / "web" / "sala.js").read_text(encoding="utf-8")
    doc = (RAIZ / "notas" / "seguranca" / "grupos.md").read_text(encoding="utf-8")
    pares = [("c_max_ops_por_minuto constant int := 300", "MAX_OPS_POR_MINUTO = 300"),
             ("c_max_ops_por_hora constant int := 3000", "MAX_OPS_POR_HORA = 3000"),
             ("c_max_salas_ativas constant int := 200", "MAX_SALAS_ATIVAS = 200"),
             ("c_max_chamadas_por_minuto constant int := 30", "MAX_CHAMADAS_POR_MINUTO = 30"),
             ("c_max_ops_por_sala constant int := 5000", "MAX_OPS_POR_SALA = 5000"),
             ("c_max_bytes_por_sala constant bigint := 2097152", "MAX_BYTES_POR_SALA = 2097152"),
             ("c_salto_de_lamport constant bigint := 1000", "SALTO_DE_LAMPORT = 1000")]
    for no_sql, no_js in pares:
        assert no_sql in sql, no_sql
        assert no_js in sala_js, no_js
    for frase in ("5.000 operações", "2 MB", "300 operações por minuto", "3.000 operações por hora", "200 salas",
                  "30 chamadas por minuto", "1.000"):
        assert frase in doc, frase


def test_cada_teto_devolve_um_codigo_proprio():
    sql = _sql()
    for codigo in ("sala_no_limite", "autor_no_limite", "servidor_cheio", "muitas_chamadas", "muitas_tentativas"):
        assert codigo in sql, codigo
    assert len({"sala_no_limite", "autor_no_limite", "servidor_cheio", "muitas_chamadas"}) == 4


def test_chamada_certa_nao_grava_tentativa_e_entrar_na_sala_trava_por_conta():
    corpo = _funcao("public.entrar_na_sala")
    assert "pg_advisory_xact_lock" in corpo and corpo.index("pg_advisory_xact_lock") < corpo.index("grupos.tentativas")
    assert "values (v_uid, true)" not in corpo and "values (v_uid, false)" in corpo


def test_a_limpeza_apaga_anonimos_orfaos_com_mais_de_2_dias():
    corpo = _funcao("grupos.limpa_salas_antigas")
    assert "delete from auth.users" in corpo and "u.is_anonymous" in corpo and "interval '2 days'" in corpo
    for condicao in ("public.membros", "public.salas", "public.operacoes"):
        assert condicao in corpo


def test_o_documento_de_seguranca_traz_o_sql_novo_igual_ao_das_migracoes():
    doc = (RAIZ / "notas" / "seguranca" / "grupos.md").read_text(encoding="utf-8")
    for nome in ("grupos.tipos_de_operacao", "grupos.valida_operacao", "grupos.antes_de_criar_sala", "public.cria_sala",
                 "public.entrar_na_sala", "grupos.antes_de_inserir_operacao", "grupos.limpa_salas_antigas"):
        assert _funcao(nome) in doc, nome
