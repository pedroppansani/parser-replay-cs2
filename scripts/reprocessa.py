"""
Reprocessa o corpus a partir do INTERIM, em paralelo, na ordem que as
dependências exigem.

    py -3.12 -m scripts.reprocessa                      # todas as partidas
    py -3.12 -m scripts.reprocessa match_16 match_20    # só algumas
    py -3.12 -m scripts.reprocessa --processos 4
    py -3.12 -m scripts.reprocessa --sequencial         # referência para conferir o paralelo
    py -3.12 -m scripts.reprocessa --reajusta-referencias

POR QUE EXISTE
--------------
`process_all_demos --force` reprocessa a partir das DEMOS no disco -- e 51 das
52 já foram apagadas (decisão 27). Não havia jeito de refazer o corpus inteiro
com o código novo: era partida a partida, à mão, na ordem certa de cabeça. E a
ordem importa, porque há passos que precisam do corpus INTEIRO pronto antes:

  1. métricas              por partida  (paralelo)   lê o interim
  2. referências globais   corpus       (sequencial) SÓ com --reajusta-referencias
  3. insights, autópsia,   por partida  (paralelo)   lê as referências
     replay
  4. perfis acumulados     corpus       (sequencial) lê o player_profile de TODAS
  5. payload da página     por partida  (paralelo)   lê os perfis acumulados
  6. manifesto             corpus       (sequencial) registra a versão nova

O `build_chain` de process_all_demos faz 3 e 5 juntos, partida a partida, e
por isso o payload de cada página embutia o perfil acumulado da rodada ANTERIOR.
Aqui o 5 só começa quando o 4 terminou.

O QUE ESTE SCRIPT NÃO FAZ, DE PROPÓSITO
---------------------------------------
Reajustar referência muda número, e é decisão, não efeito colateral de
reprocessar. Por padrão as referências globais (modelo de clusters, escala dos
papéis, economia) ficam como estão; `--reajusta-referencias` refaz as três. Os
PESOS do rating nunca são refeitos aqui: são calibração contra a HLTV
(`fit_rating --fit-pesos --gravar`), e refazer a referência de escala do rating
sem refazê-los marcaria `pesos_desatualizados` em todas as páginas.

PARALELO = SEQUENCIAL, e isso é conferido
-----------------------------------------
Cada partida escreve só na própria pasta, e os passos de corpus são barreiras.
`--sequencial` roda a mesma coisa num processo só; o teste
`tests/test_reprocessa.py` e a conferência registrada no CLAUDE.md comparam os
dois arquivo a arquivo.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import io
import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
LOGS_DIR = PROJECT_ROOT / "logs" / "reprocessa"

# Pico de memória de UM processo, medido em 2026-09-21 (match_16, 29 rounds):
# 2,33 GB nas métricas, 2,00 GB em insights+autópsia+replay. 2,5 dá margem para
# partida longa (a maior do corpus tem 36 rounds).
MEMORIA_POR_PROCESSO_GB = 2.5

# Fração da memória LIVRE que o reprocessamento pode ocupar. O resto é do
# sistema e do que mais estiver aberto -- estourar a memória faz o Windows
# paginar, e aí o paralelo fica mais lento que o sequencial.
FRACAO_DA_MEMORIA_LIVRE = 0.7

# Teto de processos mesmo com memória sobrando: acima disso os processos
# disputam núcleo e disco, e o ganho some.
MAX_PROCESSOS = 8

# Quantos processos rodam juntos. None = calcula pela memória livre e pelos
# núcleos (`processos_padrao`); um número fixa. `--processos` na linha de
# comando vence os dois. É aqui que se baixa se a máquina tiver menos memória.
PROCESSOS: int | None = None

# Intervalo da amostragem de memória livre durante o reprocessamento.
AMOSTRA_MEMORIA_S = 0.25


# ---------------------------------------------------------------------------
# Quantos processos
# ---------------------------------------------------------------------------

def _memoria_livre_gb() -> float | None:
    """Memória física livre, pelo Windows (sem psutil, que não é dependência)."""
    if sys.platform != "win32":
        return None

    class _Status(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    st = _Status()
    st.dwLength = ctypes.sizeof(_Status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return None
    return st.ullAvailPhys / 1e9


def _pico_do_processo_gb() -> float | None:
    """Pico de memória (working set) DESTE processo desde que ele nasceu."""
    if sys.platform != "win32":
        return None
    from ctypes import wintypes

    class _Contadores(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    c = _Contadores()
    c.cb = ctypes.sizeof(_Contadores)
    if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
        return None
    return c.PeakWorkingSetSize / 1e9


class MedidorDeMemoria:
    """Amostra a memória LIVRE do sistema enquanto o reprocessamento roda.

    O pico do paralelo é a maior queda da memória livre em relação ao início --
    é o que a máquina sentiu de fato, com todos os processos juntos, e não a
    soma de estimativas por processo.
    """

    def __init__(self) -> None:
        import threading

        self.livre_inicio = _memoria_livre_gb()
        self.livre_minima = self.livre_inicio
        self._parar = threading.Event()
        self._fio = threading.Thread(target=self._amostra, daemon=True)

    def _amostra(self) -> None:
        while not self._parar.wait(AMOSTRA_MEMORIA_S):
            agora = _memoria_livre_gb()
            if agora is not None and (self.livre_minima is None or agora < self.livre_minima):
                self.livre_minima = agora

    def __enter__(self) -> "MedidorDeMemoria":
        self._fio.start()
        return self

    def __exit__(self, *_) -> None:
        self._parar.set()
        self._fio.join()

    @property
    def pico_gb(self) -> float | None:
        if self.livre_inicio is None or self.livre_minima is None:
            return None
        return self.livre_inicio - self.livre_minima


def processos_padrao() -> int:
    """O menor entre: metade dos núcleos, o que cabe na memória livre, e o teto."""
    nucleos = max(1, (os.cpu_count() or 2) // 2)
    livre = _memoria_livre_gb()
    por_memoria = (int(livre * FRACAO_DA_MEMORIA_LIVRE // MEMORIA_POR_PROCESSO_GB)
                   if livre is not None else nucleos)
    return max(1, min(nucleos, por_memoria, MAX_PROCESSOS))


# ---------------------------------------------------------------------------
# O que cada processo faz (funções de módulo: o Windows cria processo por
# spawn e precisa importá-las pelo nome)
# ---------------------------------------------------------------------------

def _roda(match_id: str, etapa: str) -> tuple[str, str, float, str | None, float | None]:
    """Uma etapa de uma partida. A saída vai para um log por partida -- seis
    processos imprimindo juntos no terminal não se leem."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log = LOGS_DIR / f"{match_id}-{etapa}.log"
    t0 = time.time()
    buffer = io.StringIO()
    erro = None
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            if etapa == "metricas":
                from scripts.process_demo import process

                meta = json.loads((PROCESSED_DIR / match_id / "match_meta.json").read_text(encoding="utf-8"))
                # o source_dem é só registro: com from_interim a demo não é lida
                process(Path(meta["source_dem"]), match_id, from_interim=True)
            elif etapa == "insights":
                from scripts import build_breakdown, build_insights, export_replay

                build_insights.build(match_id)
                build_breakdown.build(match_id)
                export_replay.build(match_id)
            elif etapa == "payload":
                from scripts import export_web_payload

                export_web_payload.build(match_id)
            else:
                raise ValueError(f"etapa desconhecida: {etapa}")
    except Exception:
        erro = traceback.format_exc()
        buffer.write("\n" + erro)
    log.write_text(buffer.getvalue(), encoding="utf-8")
    return match_id, etapa, time.time() - t0, erro, _pico_do_processo_gb()


def _etapa_por_partida(ids: list[str], etapa: str, processos: int) -> dict[str, str]:
    """Roda uma etapa em todas as partidas; devolve {match_id: erro} das que falharam."""
    falhas: dict[str, str] = {}
    picos: list[float] = []
    t0 = time.time()
    with MedidorDeMemoria() as medidor:
        if processos <= 1:
            for mid in ids:
                mid, _, seg, erro, pico = _roda(mid, etapa)
                _anuncia(mid, etapa, seg, erro, falhas)
        else:
            with ProcessPoolExecutor(max_workers=processos) as pool:
                futuros = [pool.submit(_roda, mid, etapa) for mid in ids]
                for f in as_completed(futuros):
                    mid, _, seg, erro, pico = f.result()
                    _anuncia(mid, etapa, seg, erro, falhas)
                    if pico is not None:
                        picos.append(pico)
    memoria = ""
    if medidor.pico_gb is not None:
        memoria = f"; memória: pico {medidor.pico_gb:.1f} GB acima do início"
        if picos:
            memoria += f", maior processo {max(picos):.2f} GB"
    print(f"  {etapa}: {len(ids) - len(falhas)}/{len(ids)} em {time.time() - t0:.1f}s{memoria}")
    return falhas


def _anuncia(mid: str, etapa: str, seg: float, erro: str | None, falhas: dict) -> None:
    if erro:
        falhas[mid] = erro.strip().splitlines()[-1]
        print(f"    FALHOU {mid} ({etapa}, {seg:.1f}s): {falhas[mid]}")


def _passo_de_corpus(nome: str, funcao) -> None:
    """Um passo que precisa do corpus inteiro. Roda no processo principal.

    O `sys.argv` é trocado durante a chamada porque fit_global_clusters e
    fit_archetype_reference têm argparse no main(): chamados daqui, leriam os
    argumentos DESTE script (`--processos 4`) e parariam com erro -- ou pior,
    aceitariam um que por acaso tenha o mesmo nome.
    """
    t0 = time.time()
    buffer = io.StringIO()
    argv_original = sys.argv
    sys.argv = [nome]
    try:
        with contextlib.redirect_stdout(buffer):
            funcao()
    finally:
        sys.argv = argv_original
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (LOGS_DIR / f"_corpus-{nome}.log").write_text(buffer.getvalue(), encoding="utf-8")
    print(f"  {nome}: {time.time() - t0:.1f}s")


# ---------------------------------------------------------------------------
# A ordem
# ---------------------------------------------------------------------------

def partidas_reprocessaveis(pedidas: list[str] | None = None) -> list[str]:
    """Partidas com processado E interim: sem o interim não há de onde refazer."""
    todas = sorted(d.name for d in PROCESSED_DIR.glob("match_*") if d.is_dir())
    ids = pedidas or todas
    sem_interim = [m for m in ids if not (INTERIM_DIR / m / "ticks.parquet").exists()]
    if sem_interim:
        raise SystemExit(f"sem interim, não dá para reprocessar: {sem_interim}")
    return ids


def reprocessa(ids: list[str], processos: int, reajusta_referencias: bool = False) -> dict[str, str]:
    """As seis etapas, com barreira entre elas. Devolve as falhas."""
    # Polars usa todos os núcleos por padrão; com N processos isso dá N x núcleos
    # threads disputando a CPU. O ambiente é herdado pelos processos filhos, e o
    # Polars lê a variável quando é importado lá.
    os.environ["POLARS_MAX_THREADS"] = str(max(1, (os.cpu_count() or 2) // max(1, processos)))

    falhas: dict[str, str] = {}

    def vivos() -> list[str]:
        return [m for m in ids if m not in falhas]

    print(f"[1/6] métricas por partida ({processos} processo(s))")
    falhas |= _etapa_por_partida(vivos(), "metricas", processos)

    if reajusta_referencias:
        print("[2/6] referências globais (clusters, papéis, economia; pesos do rating NÃO)")
        from scripts import fit_archetype_reference, fit_economia, fit_global_clusters

        _passo_de_corpus("fit_global_clusters", fit_global_clusters.main)
        _passo_de_corpus("fit_archetype_reference", fit_archetype_reference.main)
        _passo_de_corpus("fit_economia", fit_economia.main)
    else:
        print("[2/6] referências globais: mantidas (use --reajusta-referencias para refazer)")

    print("[3/6] insights, autópsia e replay por partida")
    falhas |= _etapa_por_partida(vivos(), "insights", processos)

    print("[4/6] perfis acumulados (corpus)")
    from scripts import build_player_profiles

    _passo_de_corpus("build_player_profiles", build_player_profiles.main)

    print("[5/6] payload da página por partida")
    falhas |= _etapa_por_partida(vivos(), "payload", processos)

    print("[6/6] manifesto")
    from scripts import manifest

    _passo_de_corpus("manifest", lambda: manifest.atualiza(vivos()))
    return falhas


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Reprocessa o corpus a partir do interim.")
    ap.add_argument("match_ids", nargs="*", help="partidas (padrão: todas)")
    ap.add_argument("--processos", type=int, default=None,
                    help=f"processos em paralelo (padrão: calculado; hoje {processos_padrao()})")
    ap.add_argument("--sequencial", action="store_true", help="um processo só (referência)")
    ap.add_argument("--reajusta-referencias", action="store_true",
                    help="refaz clusters, escala dos papéis e economia (nunca os pesos do rating)")
    args = ap.parse_args(argv)

    ids = partidas_reprocessaveis(args.match_ids or None)
    processos = 1 if args.sequencial else (args.processos or PROCESSOS or processos_padrao())
    t0 = time.time()
    print(f"reprocessando {len(ids)} partida(s) a partir do interim; logs em "
          f"{LOGS_DIR.relative_to(PROJECT_ROOT).as_posix()}/")
    falhas = reprocessa(ids, processos, args.reajusta_referencias)
    print(f"\ntotal: {time.time() - t0:.1f}s, {len(ids) - len(falhas)}/{len(ids)} partidas completas")
    if falhas:
        print("FALHAS (a partida parou na etapa indicada; o log tem o traceback):")
        for mid, erro in falhas.items():
            print(f"  {mid}: {erro}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
