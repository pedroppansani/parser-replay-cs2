"""Importação de demos baixadas à mão: identidade pelo sha256, nada apagado."""
from __future__ import annotations

import hashlib
import zipfile

import pytest

from scripts import clean_match as cm
from scripts import importa_demos as imp
from scripts import manifest as mf


@pytest.fixture
def cenario(tmp_path, monkeypatch):
    boa = b"demo-que-confere" * 100
    esperada_de_outra = b"conteudo-original" * 100
    monkeypatch.setattr(mf, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mf, "MANIFEST_FILE", tmp_path / "manifest.json")
    monkeypatch.setattr(imp, "PROJECT_ROOT", tmp_path)
    backup = tmp_path / "BACKUP"
    backup.mkdir()
    monkeypatch.setattr(cm, "pastas_de_backup", lambda: [backup])
    mf.salva({"formato": 1, "partidas": {
        "match_10": {"match_id": "match_10", "demos": [{
            "arquivo": "a-vs-b-m1-dust2.dem", "caminho": "demos/serie-x/a-vs-b-m1-dust2.dem",
            "sha256": hashlib.sha256(boa).hexdigest()}]},
        "match_11": {"match_id": "match_11", "demos": [{
            "arquivo": "a-vs-b-m2-anubis.dem", "caminho": "demos/serie-x/a-vs-b-m2-anubis.dem",
            "sha256": hashlib.sha256(esperada_de_outra).hexdigest()}]},
    }})
    entrada = tmp_path / "demos" / "entrada"
    entrada.mkdir(parents=True)
    pacote = entrada / "serie-x.zip"
    with zipfile.ZipFile(pacote, "w") as z:
        z.writestr("a-vs-b-m1-dust2.dem", boa)                  # confere
        z.writestr("a-vs-b-m2-anubis.dem", b"outra coisa" * 50)  # mesmo nome, hash divergente
        z.writestr("a-vs-b-m3-nuke.dem", b"mapa fora" * 50)      # fora do manifesto
    return tmp_path, entrada, pacote, backup, boa


def test_importa_pelo_hash_e_copia_para_o_backup(cenario):
    raiz, entrada, pacote, backup, boa = cenario
    r = imp.importa(entrada=entrada)
    assert [x["match_id"] for x in r["importados"]] == ["match_10"]
    alvo = raiz / "demos/serie-x/a-vs-b-m1-dust2.dem"
    assert alvo.read_bytes() == boa
    copia = backup / "demos" / "a-vs-b-m1-dust2.dem"
    assert copia.read_bytes() == boa and r["importados"][0]["copia"] == str(copia)
    assert hashlib.sha256(boa).hexdigest() in (backup / "SHA256SUMS.txt").read_text(encoding="utf-8")


def test_hash_divergente_nao_entra_e_e_listado(cenario):
    raiz, entrada, *_ = cenario
    r = imp.importa(entrada=entrada)
    assert [x["partidas_com_esse_nome"] for x in r["divergentes"]] == [["match_11"]]
    assert not (raiz / "demos/serie-x/a-vs-b-m2-anubis.dem").exists()


def test_fora_do_manifesto_fica_na_entrada_e_nada_e_apagado(cenario):
    raiz, entrada, pacote, *_ = cenario
    r = imp.importa(entrada=entrada)
    assert len(r["fora_do_corpus"]) == 1 and r["fora_do_corpus"][0]["arquivo"].endswith("a-vs-b-m3-nuke.dem")
    assert pacote.exists()                                               # o pacote fica
    assert (entrada / "_extraido/serie-x/a-vs-b-m3-nuke.dem").exists()   # o fora do corpus fica
    assert (entrada / "_extraido/serie-x/a-vs-b-m2-anubis.dem").exists() # o divergente fica


def test_simular_nao_move_nem_extrai(cenario):
    raiz, entrada, *_ = cenario
    imp.importa(simular=True, entrada=entrada)
    assert not (entrada / "_extraido").exists()
    assert not (raiz / "demos/serie-x").exists()


def test_rodar_de_novo_nao_duplica(cenario):
    raiz, entrada, *_ = cenario
    imp.importa(entrada=entrada)
    r = imp.importa(entrada=entrada)
    assert r["importados"] == [] and len(r["divergentes"]) == 1


def test_pacote_extraido_pelo_tar(tmp_path):
    """O .rar da HLTV sai pelo tar do sistema (libarchive); aqui, um .tar.gz
    exercita o mesmo caminho."""
    import tarfile
    arq = tmp_path / "x.dem"
    arq.write_bytes(b"conteudo" * 10)
    pacote = tmp_path / "serie.tar.gz"
    with tarfile.open(pacote, "w:gz") as t:
        t.add(arq, arcname="x.dem")
    destino = tmp_path / "saida"
    assert imp.extrai(pacote, destino) is None
    assert (destino / "x.dem").read_bytes() == arq.read_bytes()
