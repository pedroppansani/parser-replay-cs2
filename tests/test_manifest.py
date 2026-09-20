"""
Manifesto das demos e limpeza segura (Fase 0).

A limpeza apaga arquivos de 300MB que não voltam sem baixar de novo. Os testes
que apagam de verdade rodam numa pasta temporária; os que olham as partidas
reais só simulam.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import clean_match as cm
from scripts import manifest as mf

ROOT = Path(__file__).resolve().parent.parent

# O GitHub recusa arquivo acima de 100MB; o aviso começa em 50MB. Um arquivo
# versionado passando disso é quase sempre uma demo ou um parquet de ticks que
# escapou do .gitignore.
MAX_MB_VERSIONADO = 50


def test_nenhum_arquivo_versionado_passa_do_limite():
    try:
        nomes = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                               check=True).stdout.decode().split("\0")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git indisponível")
    grandes = [n for n in nomes if n and (ROOT / n).is_file()
               and (ROOT / n).stat().st_size > MAX_MB_VERSIONADO * 1e6]
    assert not grandes, grandes


def test_demo_fica_fora_do_git_em_qualquer_pasta():
    for caminho in ("demos/a.dem", "data/raw/b.dem", "outra/pasta/c.dem", "d.dem.gz"):
        r = subprocess.run(["git", "check-ignore", "-q", caminho], cwd=ROOT)
        assert r.returncode == 0, f"{caminho} não está ignorado"


def test_manifesto_tem_toda_partida_processada_com_identidade_da_demo():
    if not mf.MANIFEST_FILE.exists():
        pytest.skip("manifesto ainda não gerado")
    partidas = json.loads(mf.MANIFEST_FILE.read_text(encoding="utf-8"))["partidas"]
    processadas = {p.name for p in mf.PROCESSED_DIR.glob("match_*") if p.is_dir()}
    assert processadas <= partidas.keys(), processadas - partidas.keys()
    for mid, linha in partidas.items():
        assert linha["demos"], mid
        for d in linha["demos"]:
            assert len(d.get("sha256", "")) == 64, (mid, d.get("arquivo"))
            # versionado: nada de caminho absoluto da máquina de quem processou
            assert not Path(d["caminho"]).is_absolute() and ":" not in d["caminho"], d["caminho"]
        # data sem procedência seria data inventada
        assert (linha["data"] is None) == (linha["fonte_da_data"] is None), mid


def test_simulacao_nao_apaga_nada():
    if not mf.MANIFEST_FILE.exists():
        pytest.skip("manifesto ainda não gerado")
    mid = sorted(json.loads(mf.MANIFEST_FILE.read_text(encoding="utf-8"))["partidas"])[-1]
    antes = {p: p.exists() for p in cm._alvos(mid, manter_interim=False)}
    r = cm.limpa(mid, confirmar=False)
    assert r.get("simulado") is True or not r["ok"]
    assert {p: p.exists() for p in antes} == antes


@pytest.fixture
def partida_falsa(tmp_path, monkeypatch):
    """Uma partida inteira numa pasta temporária: demo, interim e manifesto."""
    demo = tmp_path / "demos" / "a-vs-b-m1-mirage.dem"
    demo.parent.mkdir(parents=True)
    demo.write_bytes(b"x" * 1000)
    interim = tmp_path / "interim" / "match_99"
    interim.mkdir(parents=True)
    (interim / "ticks.parquet").write_bytes(b"y" * 500)

    monkeypatch.setattr(mf, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mf, "MANIFEST_FILE", tmp_path / "manifest.json")
    monkeypatch.setattr(cm, "INTERIM_DIR", tmp_path / "interim")
    mf.salva({"formato": 1, "partidas": {"match_99": {
        "match_id": "match_99", "limpeza": None,
        "demos": [{"arquivo": demo.name, "caminho": "demos/" + demo.name, "sha256": "0" * 64}],
    }}})
    return demo, interim


def test_processado_incompleto_nao_deixa_limpar(partida_falsa, monkeypatch):
    demo, interim = partida_falsa
    monkeypatch.setattr(cm, "verifica", lambda mid: ["falta web_payload.json"])
    r = cm.limpa("match_99", confirmar=True)
    assert not r["ok"] and r["problemas"] == ["falta web_payload.json"]
    assert demo.exists() and interim.exists()


def test_limpeza_apaga_e_registra_no_manifesto(partida_falsa, monkeypatch):
    demo, interim = partida_falsa
    monkeypatch.setattr(cm, "verifica", lambda mid: [])
    r = cm.limpa("match_99", confirmar=True, manter_interim=False)
    assert r["ok"] and not demo.exists() and not interim.exists()
    linha = mf.carrega()["partidas"]["match_99"]
    assert linha["limpeza"]["bytes_liberados"] == 1500
    assert "demos/a-vs-b-m1-mirage.dem" in linha["limpeza"]["removidos"]
    assert linha["demos"][0]["existe"] is False
    assert linha["demos"][0]["sha256"] == "0" * 64          # a identidade fica


def test_o_padrao_apaga_so_a_demo(partida_falsa, monkeypatch):
    """Decisão do Pedro: os dados crus ficam, e a partida continua recalculável."""
    demo, interim = partida_falsa
    monkeypatch.setattr(cm, "verifica", lambda mid: [])
    cm.limpa("match_99", confirmar=True)
    assert not demo.exists() and interim.exists()


def test_verificacao_pega_placar_impossivel(tmp_path, monkeypatch):
    import polars as pl

    d = tmp_path / "match_98"
    d.mkdir()
    for nome in cm.ARQUIVOS_OBRIGATORIOS:
        if nome.endswith(".json"):
            (d / nome).write_text("{}", encoding="utf-8")
    pl.DataFrame({"round_num": list(range(1, 25))}).write_parquet(d / "rounds.parquet")
    for nome in ("adr_summary.parquet", "kast_summary.parquet"):
        pl.DataFrame({"x": [1]}).write_parquet(d / nome)
    (d / "match_meta.json").write_text('{"n_rounds": 24}', encoding="utf-8")
    (d / "insights.json").write_text('{"match": {"score_a": 15, "score_b": 9}}', encoding="utf-8")
    monkeypatch.setattr(cm, "PROCESSED_DIR", tmp_path)
    problemas = cm.verifica("match_98")
    assert any("placar impossível" in p for p in problemas)


def test_atualizar_o_manifesto_nunca_apaga_um_sha256_ja_medido(tmp_path, monkeypatch):
    """O hash é a identidade PERMANENTE da demo -- ele sobrevive ao arquivo.

    REGRESSÃO (2026-09-20): ao ensinar o manifesto a reencontrar uma demo que
    mudou de pasta, o registro anterior passou a ser procurado por um caminho
    que não existia mais. Sem `anterior`, `_demo` regravava a linha sem o hash,
    e uma rodada do script apagou o sha256 das 52 partidas de uma vez -- num
    arquivo versionado, cujo motivo de existir é justamente não perder isso
    depois que a demo é apagada.
    """
    sumida = tmp_path / "demos" / "sumiu.dem"
    anterior = {"arquivo": "sumiu.dem", "caminho": "demos/sumiu.dem", "existe": True,
                "bytes": 123, "mtime": 456, "sha256": "a" * 64}
    linha = mf._demo(sumida, anterior)
    assert linha["existe"] is False
    assert linha["sha256"] == "a" * 64, "o hash medido quando o arquivo existia se perdeu"
    assert linha["bytes"] == 123 and linha["mtime"] == 456


def test_demo_que_mudou_de_pasta_e_reencontrada_e_o_caminho_antigo_fica_registrado(tmp_path, monkeypatch):
    """A demo muda de lugar (extraída de novo, pasta " - Copia"). O manifesto
    reencontra pelo hash e ANOTA de onde ela saiu -- caminho trocado em silêncio
    é a próxima pergunta sem resposta."""
    monkeypatch.setattr(mf, "PROJECT_ROOT", tmp_path)
    nova = tmp_path / "demos" / "pasta nova"
    nova.mkdir(parents=True)
    arquivo = nova / "partida.dem"
    arquivo.write_bytes(b"demo de verdade")
    sha = mf.sha256_do_arquivo(arquivo)

    antigo = tmp_path / "demos" / "pasta velha" / "partida.dem"
    linha = mf._demo(antigo, {"arquivo": "partida.dem", "caminho": "demos/pasta velha/partida.dem",
                              "existe": True, "sha256": sha})
    assert linha["existe"] is True
    assert linha["caminho"] == "demos/pasta nova/partida.dem"
    assert linha["caminho_anterior"] == "demos/pasta velha/partida.dem"
    assert linha["sha256"] == sha
