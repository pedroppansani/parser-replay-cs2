"""
As fontes do site lidas com as partes incluídas (decisão 50): a linha `//@inclui` vira o conteúdo da parte, tal como
está; arquivo sem inclusão fica igual; parte que falta ou que inclui outra para o build. (A guarda do cartão 9, o
sha256 do `template.html` e do `tactics.js` de antes da divisão, saiu com o cartão fechado, OK do Pedro.)
"""
from __future__ import annotations

import pytest

from scripts.fontes_web import le_fonte


def test_a_linha_de_inclusao_vira_a_parte_tal_como_esta(tmp_path):
    (tmp_path / "partes").mkdir()
    (tmp_path / "partes" / "a.js").write_text("  const a = 1;\n", encoding="utf-8")
    (tmp_path / "partes" / "b.js").write_text("// b\nconst b = 2;\n\n", encoding="utf-8")
    (tmp_path / "f.js").write_text("antes\n//@inclui partes/a.js\nmeio\n//@inclui partes/b.js\ndepois //@inclui x\n",
                                   encoding="utf-8")
    assert le_fonte(tmp_path / "f.js") == "antes\n  const a = 1;\nmeio\n// b\nconst b = 2;\n\ndepois //@inclui x\n"


def test_sem_linha_de_inclusao_e_o_arquivo_como_esta(tmp_path):
    (tmp_path / "f.html").write_text("<p>x</p>\n  //@inclui recuada.js\n", encoding="utf-8")
    assert le_fonte(tmp_path / "f.html") == (tmp_path / "f.html").read_text(encoding="utf-8")


def test_parte_que_falta_ou_que_inclui_outra_para_o_build(tmp_path):
    (tmp_path / "f.js").write_text("//@inclui falta.js\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        le_fonte(tmp_path / "f.js")
    (tmp_path / "g.js").write_text("//@inclui h.js\n", encoding="utf-8")
    (tmp_path / "h.js").write_text("//@inclui i.js\n", encoding="utf-8")
    with pytest.raises(ValueError, match="uma parte não inclui outra"):
        le_fonte(tmp_path / "g.js")
