"""
As fontes do site lidas com as partes incluídas (cartão 9, decisão 50).

A guarda do cartão 9: o `le_fonte` do `template.html` e do `tactics.js` devolve EXATAMENTE o texto de antes da
divisão (o sha256 do arquivo na main `f7bc788a`, lido como o build lê). Enquanto as fontes são divididas em partes,
este teste não muda; quando o cartão fechar, ele sai com o OK do Pedro (a partir daí, mudar a fonte de propósito muda o
hash). E o mecanismo: a linha `//@inclui` vira o conteúdo da parte, tal como está; parte que falta ou que inclui outra
para o build.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.fontes_web import le_fonte

WEB = Path(__file__).resolve().parents[1] / "dashboard" / "web"
SHA256_ANTES_DA_DIVISAO = {   # main f7bc788a, o texto lido com read_text(encoding="utf-8"), em UTF-8
    "template.html": "f08957c85d1b3afccf8db9f9abd1a30347372cff48a9cd659a3f166c6a56966a",
    "tactics.js": "44326be6adde67c4c18b9e661924d7b253c4217be05293cfab224d505a49f39a",
}


@pytest.mark.parametrize("nome", sorted(SHA256_ANTES_DA_DIVISAO))
def test_le_fonte_devolve_o_texto_de_antes_da_divisao(nome):
    assert hashlib.sha256(le_fonte(WEB / nome).encode("utf-8")).hexdigest() == SHA256_ANTES_DA_DIVISAO[nome]


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
