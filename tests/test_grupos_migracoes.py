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
    assert len(nomes) == 5
    assert all(re.match(r"^\d{14}_grupos_[a-z_]+\.sql$", n) for n in nomes), nomes


def test_rls_ligado_em_toda_tabela_criada():
    sql = _sql()
    tabelas = re.findall(r"create table (\w+\.\w+)", sql)
    assert set(tabelas) == {"public.salas", "public.membros", "public.operacoes", "grupos.tentativas", "grupos.expulsos"}
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
    assert sum(l.startswith("ok") for l in linhas) >= 60
