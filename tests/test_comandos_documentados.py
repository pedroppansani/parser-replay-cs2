"""Todo comando `py -3.12 -m <pacote>.<módulo>` citado na documentação existe
(auditoria, item 5.6: scripts foram separados em scripts/, scripts/calibracao/,
pesquisa/, leitura/ e legado/)."""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
COMANDO = re.compile(r"(?:py -3\.1\d|python)(?: -W ignore)? -m ((?:scripts|pesquisa|metrics|leitura|parsing|clustering)"
                     r"(?:\.[a-z_0-9]+)+)")


def _documentos():
    yield RAIZ / "CLAUDE.md"
    yield RAIZ / "README.md"
    yield from sorted((RAIZ / "notas").rglob("*.md"))
    yield from (p for p in sorted(RAIZ.glob("*.md")) if p.name not in ("CLAUDE.md", "README.md"))


def test_todo_comando_citado_aponta_para_um_modulo_que_existe():
    faltando = []
    for doc in _documentos():
        for mod in COMANDO.findall(doc.read_text(encoding="utf-8")):
            caminho = RAIZ / (mod.replace(".", "/") + ".py")
            if not caminho.exists() and not (RAIZ / mod.replace(".", "/") / "__main__.py").exists():
                faltando.append(f"{doc.relative_to(RAIZ).as_posix()}: {mod}")
    assert not faltando, faltando


def test_os_exploratorios_moram_em_pesquisa_e_a_logica_de_teste_nao():
    soltos = [p.name for p in (RAIZ / "scripts").glob("*.py")
              if re.match(r"(investiga|prototipo|verifica|valida|piora|casos|proposta)_", p.name)
              or p.name == "compara_lido_inferido.py"]
    assert not soltos, soltos
    for t in (RAIZ / "tests").glob("test_*.py"):
        assert not re.search(r"^\s*(from|import) pesquisa\b", t.read_text(encoding="utf-8"), re.M), t.name
    assert not (RAIZ / "dashboard" / "app.py").exists() and (RAIZ / "legado" / "app.py").exists()
    assert "streamlit" not in (RAIZ / "requirements.txt").read_text(encoding="utf-8")
