"""Nenhum número sobre o corpus, a validação ou uma contagem é escrito à mão
no template: todos vêm de `data/processed/numeros_citaveis.json`, pelo build.

O teste estrutural lê o texto VISÍVEL do template (o HTML estático e as strings
do JavaScript) e recusa qualquer dígito ou número por extenso que descreva o
corpus. As exceções estão listadas com o motivo."""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATE = RAIZ / "dashboard" / "web" / "template.html"

EXTENSO = r"(?:duas|dois|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|vinte|trinta|cinquenta)"
# "um" e "uma" ficam de fora: são artigo ("uma partida", "um round")
NUMERO = rf"(?:\d[\d.,]*|{EXTENSO})"
# o que um número de corpus/validação/contagem descreve
ALVOS = r"(?:partidas?|demos?|mapas?|times?|jogador(?:es)?[- ]rounds?|jogador[- ]partidas?|jogadores|rounds?|kills|jeitos|grupos|testes)"
PADROES = [
    re.compile(rf"\b{NUMERO}\s+{ALVOS}\b", re.I),
    re.compile(r"\d+[.,]\d+\s*°"),                 # ângulo medido (validação da convenção)
    re.compile(r"\bFACEIT\b"),                      # origem da partida, que vem do manifesto
]
# Exceções: (trecho exato, motivo). Tudo aqui é exemplo de FORMATO ou constante
# do jogo / do replay, não uma afirmação sobre o corpus.
EXCECOES = [
    ("9 de 12 rounds", "exemplo ilustrativo de como a concentração é escrita"),
    ("12 rounds", "idem (o mesmo exemplo, repetido em comentário de leitura)"),
    ("dois rounds sem contato", "exemplo do motivo de usar mediana"),
    ("4 quadros", "taxa de amostragem do replay exportado (constante do export)"),
    ("3 segundos", "recuo do replay ao clicar num evento (constante da interface)"),
]


def _texto_visivel() -> list[tuple[int, str]]:
    bruto = TEMPLATE.read_text(encoding="utf-8")
    corpo = bruto[bruto.index("</style>"):]
    base = bruto[:bruto.index("</style>")].count("\n") + 1
    out = []
    for n, linha in enumerate(corpo.split("\n"), start=base):
        s = linha.strip()
        if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            continue                                   # comentário de código não aparece na tela
        s = re.sub(r"\s//\s.*$", "", s)                # comentário no fim da linha
        trechos = re.findall(r">([^<>]+)<", s) + re.findall(r'"([^"]*)"', s) + re.findall(r"'([^']*)'", s)
        if not s.startswith("<") and "<" not in s and not re.search(r"[;{}=()]", s):
            trechos.append(s)                          # linha de texto corrido dentro de um parágrafo
        out += [(n, t) for t in trechos if re.search(r"[a-zà-ú]{3}", t, re.I)]
    return out


def test_o_template_nao_tem_numero_de_corpus_escrito_a_mao():
    achados = []
    for n, t in _texto_visivel():
        limpo = t
        for trecho, _motivo in EXCECOES:
            limpo = limpo.replace(trecho, "")
        for p in PADROES:
            for m in p.finditer(limpo):
                achados.append(f"linha {n}: {m.group(0)!r} em {t[:90]!r}")
    assert not achados, "número de corpus fixo no template:\n" + "\n".join(achados)


def test_o_controle_do_teste_estrutural_pega_o_texto_antigo():
    """O texto que a página tinha tem de ser recusado -- senão o teste acima
    não estaria medindo nada."""
    for antigo in ("Nove partidas (1.870 jogador-rounds), todas de nível", "fica a 1,76° da vítima",
                   "<span>FACEIT</span>", "Dez jogadores, 22 rounds"):
        assert any(p.search(antigo) for p in PADROES), antigo


def test_o_rodape_cita_os_numeros_do_json():
    from scripts.build_web_page import rodape_html
    from scripts.numeros_citaveis import SAIDA
    c = json.loads(SAIDA.read_text(encoding="utf-8"))
    texto = rodape_html(c)
    assert f"{c['corpus']['partidas']} partidas" in texto
    assert f"{c['corpus']['jogador_rounds']:,}".replace(",", ".") + " jogador-rounds" in texto
    assert f"{c['convencao_de_angulos']['erro_mediano_graus']:.2f}".replace(".", ",") + "°" in texto
    assert f"Os {c['estilos']['grupos']} jeitos" in texto


def test_os_numeros_do_corpus_batem_com_o_manifesto():
    from scripts.numeros_citaveis import SAIDA, corpus
    gravado = json.loads(SAIDA.read_text(encoding="utf-8"))["corpus"]
    assert gravado == corpus(), "rode py -3.12 -m scripts.numeros_citaveis"


def test_a_origem_no_cabecalho_vem_do_manifesto():
    from scripts.build_web_page import origem_da_partida
    assert origem_da_partida("match_02") == "FACEIT"
    assert origem_da_partida("match_23") not in (None, "FACEIT")


def test_as_imagens_do_readme_existem_no_repositorio():
    """O README apontava para docs/img/, que o .gitignore ignora: 404 no GitHub."""
    import subprocess
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    imagens = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    locais = [i for i in imagens if not i.startswith("http")]
    assert locais, "o README não tem imagem nenhuma"
    for i in locais:
        assert (RAIZ / i).is_file(), i
        ignorado = subprocess.run(["git", "check-ignore", "-q", i], cwd=RAIZ).returncode == 0
        assert not ignorado, f"{i} é ignorado pelo git e não chega ao GitHub"


def test_os_numeros_do_readme_sao_os_do_json_e_nao_digitados():
    """Cada bloco marcado do README tem de ser IGUAL ao gerado do JSON: quem
    editar um número à mão quebra este teste."""
    from scripts.numeros_citaveis import SAIDA, blocos_de_texto, blocos_no_texto
    doc = json.loads(SAIDA.read_text(encoding="utf-8"))
    esperado = blocos_de_texto(doc)
    escrito = blocos_no_texto((RAIZ / "README.md").read_text(encoding="utf-8"))
    assert set(escrito) == set(esperado), "bloco de números faltando no README"
    for nome, trechos in escrito.items():
        for t in trechos:
            assert t == esperado[nome], f"bloco '{nome}' do README difere do JSON: rode py -3.12 -m scripts.numeros_citaveis"


def test_fora_dos_blocos_o_readme_nao_cita_numero_de_validacao():
    """Os números citáveis só aparecem dentro dos blocos marcados."""
    texto = (RAIZ / "README.md").read_text(encoding="utf-8")
    fora = re.sub(r"<!-- numeros:inicio (\w+) -->.*?<!-- numeros:fim \1 -->", "", texto, flags=re.S)
    for padrao in (r"\b\d+ de \d+\b", r"\b0,\d{2,3}\b", r"\b\d+ (partidas|mapas|testes|jogador)", r"\d+,\d+\s*°"):
        assert not re.search(padrao, fora), (padrao, re.search(padrao, fora).group(0))
