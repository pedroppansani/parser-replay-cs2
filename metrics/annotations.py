"""
Anotações desenhadas sobre o mapa: esquema, projeção e validação.

A DECISÃO QUE SUSTENTA TUDO
---------------------------
**Todo desenho é guardado em coordenadas de JOGO, nunca em pixels de tela.**

O motivo é direto: o tamanho da tela muda o tempo inteiro -- janela redimensionada,
tela cheia, zoom, outro monitor. Guardar pixel significa que uma seta apontando
para o fundo do bombsite deixa de apontar para lá no instante em que qualquer uma
dessas coisas acontece. Guardando unidade de jogo, a seta aponta para o mesmo
lugar do mapa em qualquer tamanho, porque o que muda é só a projeção.

Consequência prática, e ela é o contrário do que parece mais fácil: ao entrar e
sair de tela cheia **não se escala a imagem pronta -- reprojetam-se as
coordenadas**. Escalar o desenho pronto acumula erro e borra o traço; reprojetar
devolve o mesmo desenho, nítido, no tamanho novo.

A transformação é a MESMA que o resto do projeto usa (`scripts/prepare_radar.py`),
nos dois sentidos: pixel -> unidade de jogo quando o usuário desenha, unidade de
jogo -> pixel quando renderiza.

POR QUE A VERSÃO DA CALIBRAÇÃO VAI JUNTO
-----------------------------------------
A correspondência entre unidade de jogo e pixel do radar foi AJUSTADA, não é uma
constante do jogo. Se ela for recalibrada depois, todo desenho antigo passa a
cair alguns pixels fora -- e cairia em silêncio, que é o pior jeito de errar.

Por isso cada arquivo carrega a impressão digital da calibração com que foi
feito. Ela não é um número que alguém precisa lembrar de incrementar: é derivada
dos próprios parâmetros, então muda exatamente quando a calibração muda.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Diretório próprio. NÃO vai em data/processed/, que é saída calculada e é
# regerada a cada reprocessamento -- anotação é trabalho humano e não pode ser
# apagada por um `process_demo`.
ANNOTATIONS_DIR = PROJECT_ROOT / "data" / "annotations"

# Versão do formato do arquivo. Sobe quando o esquema muda de forma incompatível.
FORMATO = 1

# Ferramentas aceitas. A seta é de primeira classe e não uma linha com enfeite:
# é a mais usada para explicar jogada, e quem desenha espera acertar a ponta.
FERRAMENTAS = ("caneta", "linha", "seta", "retangulo", "elipse", "texto")

# Três espessuras. Mais que isso vira menu e ninguém usa.
ESPESSURAS = (2, 4, 7)

# A cor é LIVRE (o usuário escolhe qualquer uma no seletor), mas o formato não:
# sempre "#rrggbb" minúsculo, que é o que a camada JS grava. Uma cor fora disso
# num arquivo importado é sinal de arquivo corrompido ou escrito à mão.
FORMATO_DA_COR = re.compile(r"^#[0-9a-f]{6}$")


def impressao_da_calibracao(radar: dict) -> str:
    """Identidade da calibração do radar, derivada dos próprios parâmetros.

    Curta de propósito (12 hex): ela só precisa distinguir calibrações, não
    resistir a ataque. E derivada, não manual: uma versão que alguém precisa
    lembrar de incrementar é uma versão que um dia não é incrementada.
    """
    partes = [
        str(radar.get("map")),
        f"{float(radar.get('scale_px_per_unit', 0)):.10g}",
        f"{float(radar.get('origin_x', 0)):.10g}",
        f"{float(radar.get('origin_y', 0)):.10g}",
        str(int(radar.get("width", 0))),
        str(int(radar.get("height", 0))),
    ]
    return hashlib.sha256("|".join(partes).encode()).hexdigest()[:12]


def jogo_para_pixel(x: float, y: float, radar: dict) -> tuple[float, float]:
    """Unidade de jogo -> pixel do radar. Mesma conta de `prepare_radar.py`.

    O Y é invertido porque no jogo ele cresce para o norte e na imagem cresce
    para baixo. Errar esse sinal espelha o mapa inteiro na vertical, e o desenho
    fica plausível o bastante para ninguém notar de imediato.
    """
    s = float(radar["scale_px_per_unit"])
    return (x - float(radar["origin_x"])) * s, (float(radar["origin_y"]) - y) * s


def pixel_para_jogo(px: float, py: float, radar: dict) -> tuple[float, float]:
    """Pixel do radar -> unidade de jogo. A inversa exata da de cima."""
    s = float(radar["scale_px_per_unit"])
    return px / s + float(radar["origin_x"]), float(radar["origin_y"]) - py / s


def caixa_do_mapa(largura_disponivel: float, altura_disponivel: float,
                  radar: dict) -> dict:
    """Onde o mapa cabe numa área, preservando a PROPORÇÃO.

    O mapa cresce até o limite da menor dimensão e fica centralizado, com o
    excedente virando espaço vazio -- nunca esticado. Já houve bug de proporção
    neste projeto (dado em retrato num canvas em paisagem), e esticar é
    exatamente o que produz aquilo.
    """
    w, h = float(radar["width"]), float(radar["height"])
    escala = min(largura_disponivel / w, altura_disponivel / h)
    largura, altura = w * escala, h * escala
    return {
        "escala": escala,
        "largura": largura,
        "altura": altura,
        "offset_x": (largura_disponivel - largura) / 2,
        "offset_y": (altura_disponivel - altura) / 2,
        "proporcao": largura / altura,
    }


def documento_vazio(match_id: str, radar: dict) -> dict:
    """Um arquivo de anotações novo, já com a procedência registrada."""
    return {
        "formato": FORMATO,
        "match_id": match_id,
        "mapa": radar.get("map"),
        "calibracao": impressao_da_calibracao(radar),
        # Uma lista de traços por round. Trocar de round troca o conjunto: nada
        # de rabisco de um round vazando no outro.
        "rounds": {},
    }


def valida(doc: dict, radar: dict | None = None) -> list[str]:
    """Problemas encontrados no documento. Lista vazia = está bom.

    Devolve TODOS os problemas em vez de levantar no primeiro: quem está
    conferindo um arquivo quer a lista inteira, não uma descoberta por execução.
    """
    erros = []
    if doc.get("formato") != FORMATO:
        erros.append(f"formato {doc.get('formato')} desconhecido (esperado {FORMATO})")
    if not doc.get("match_id"):
        erros.append("sem match_id")
    if not doc.get("calibracao"):
        erros.append("sem impressão da calibração do radar")

    if radar is not None and doc.get("calibracao"):
        atual = impressao_da_calibracao(radar)
        if atual != doc["calibracao"]:
            erros.append(
                f"calibração do radar mudou ({doc['calibracao']} -> {atual}): "
                "as anotações precisam ser reprojetadas"
            )

    atual = impressao_da_calibracao(radar) if radar is not None else None
    for rn, tracos in (doc.get("rounds") or {}).items():
        for i, t in enumerate(tracos):
            onde = f"round {rn}, traço {i}"
            if t.get("ferramenta") not in FERRAMENTAS:
                erros.append(f"{onde}: ferramenta '{t.get('ferramenta')}' desconhecida")
            if "cor" in t and not FORMATO_DA_COR.match(str(t["cor"])):
                erros.append(f"{onde}: cor {t['cor']!r} fora do formato #rrggbb")
            # Cada traço carrega a calibração com que foi feito: um arquivo pode
            # juntar traços de antes e depois de uma recalibração, e só o traço
            # sabe de qual lado ele está.
            if atual and t.get("calibracao") and t["calibracao"] != atual:
                erros.append(f"{onde}: feito com a calibração {t['calibracao']}, "
                             f"a atual é {atual} -- precisa ser reprojetado")
            pontos = t.get("pontos") or []
            if not pontos:
                erros.append(f"{onde}: sem pontos")
            for p in pontos:
                if not (isinstance(p, (list, tuple)) and len(p) == 2):
                    erros.append(f"{onde}: ponto malformado {p!r}")
                    break
    return erros


def caminho(match_id: str) -> Path:
    return ANNOTATIONS_DIR / f"{match_id}.json"


def carrega(match_id: str) -> dict | None:
    p = caminho(match_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def salva(doc: dict) -> Path:
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    p = caminho(doc["match_id"])
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def tracos_do_round(doc: dict, round_num: int) -> list[dict]:
    """Só os traços daquele round. A separação é do formato, não da interface."""
    return list((doc.get("rounds") or {}).get(str(round_num), []))
