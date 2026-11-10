"""Os callouts do Pedro como dado (C0b, `data/reference/callouts_br.csv`): forma da tabela, conferência por mapa, decisões de leitura e imagens fora do repo."""
from __future__ import annotations

import csv
import subprocess
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "data" / "reference" / "callouts_br.csv"
COLUNAS = ["mapa", "andar", "nome", "apelidos", "qualificacao", "posicao_vertical", "tipo", "x", "y", "lugar_da_demo", "lugares_na_borda", "repete_no_mapa",
           "texto_original", "observacao", "fonte", "conferido"]


def _linhas():
    return list(csv.DictReader(open(CSV, encoding="utf-8-sig"), delimiter=";"))


def test_a_tabela_tem_as_colunas_e_os_10_mapas():
    with open(CSV, encoding="utf-8-sig") as f:
        assert next(csv.reader(f, delimiter=";")) == COLUNAS
    assert {l["mapa"] for l in _linhas()} == {"de_ancient", "de_anubis", "de_cache", "de_dust2", "de_inferno", "de_mirage", "de_nuke", "de_overpass", "de_train", "de_vertigo"}


def test_todo_ponto_tem_nome_sem_interrogacao_posicao_e_fonte():
    for l in _linhas():
        assert l["nome"].strip() and "?" not in l["nome"], l                       # dúvida de leitura não entra como nome
        assert l["x"].lstrip("-").isdigit() and l["y"].lstrip("-").isdigit(), l
        assert l["fonte"] == "mapas de callouts do Pedro, 2026-11-09", l
        assert l["conferido"] in ("sim", "não"), l


def test_so_mirage_e_dust2_estao_conferidos():
    c = Counter((l["mapa"], l["conferido"]) for l in _linhas())
    assert {m for (m, v) in c if v == "sim"} == {"de_mirage", "de_dust2"}
    assert all(l["conferido"] == "não" for l in _linhas() if l["mapa"] not in ("de_mirage", "de_dust2"))


def test_as_letras_dos_bombsites_caem_nos_bombsites_da_demo():
    """A conferência independente do alinhamento: o A e o B do Pedro, convertidos, caem em BombsiteA e BombsiteB nos 7 mapas com tabela da demo."""
    sites = [l for l in _linhas() if l["tipo"] == "bombsite" and not l["lugar_da_demo"].startswith("(")]
    assert len(sites) == 14
    for l in sites:
        assert l["lugar_da_demo"] == "Bombsite" + l["nome"], l


def test_as_decisoes_de_leitura_do_pedro():
    por = {(l["mapa"], l["nome"]): l for l in _linhas()}
    assert por[("de_mirage", "Meio Falso")]["apelidos"] == "MF" and por[("de_mirage", "Meio Falso")]["qualificacao"] == ""
    assert por[("de_mirage", "Moddii")]["apelidos"] == "Mogi"
    assert por[("de_nuke", "Inferno")]["apelidos"] == "Hell"
    assert por[("de_ancient", "Caixa do Quadrado")]["apelidos"] == "Caixa do Jardim"
    assert por[("de_train", "Antigo")]["apelidos"] == "Bomb Antigo"
    assert any(l["mapa"] == "de_mirage" and l["nome"] == "Palácio" and "Tapete A" in l["apelidos"] for l in _linhas())
    for mapa in ("de_ancient", "de_anubis", "de_inferno", "de_mirage", "de_vertigo"):
        assert "Janela" in por[(mapa, "Janelão")]["apelidos"].split(" / "), mapa                                         # "janelão também pode ser janela" (2026-11-10)
    assert ("de_nuke", "Janelão") not in por and por[("de_nuke", "Janela")]["apelidos"] == ""                         # na Nuke "Janela" já é um ponto, não apelido de nada
    ls = [l for l in _linhas() if l["mapa"] == "de_mirage" and l["nome"] == "L"]
    assert len(ls) == 2 and all(l["repete_no_mapa"] for l in ls)                       # "L" repetido: o leitor pergunta qual


def test_as_imagens_do_pedro_nao_estao_no_repositorio():
    """Material de terceiros: nem copiado nem recortado. Nenhuma imagem sob data/reference nem sob pesquisa/callouts_br."""
    arqs = subprocess.run(["git", "ls-files", "data/reference", "pesquisa/callouts_br"], cwd=RAIZ, capture_output=True, text=True).stdout.split()
    assert not [a for a in arqs if a.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))]
