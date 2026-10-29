# Decisão 49: A biblioteca de arremessos num arquivo próprio, carregado depois

- **ID:** 49
- **Status:** vigente
- **Data:** 2026-10-29
- **Resumo:** No site, a biblioteca de arremessos de cada mapa sai da página da prancheta para `arremessos/<mapa>.js`, ao
  lado das páginas, e é carregada depois de a tela montar. O que precisa dela espera por ela; o modo embutido continua
  sendo o padrão do `build_html` (a página gerada sozinha).

## Texto

49. **Biblioteca de arremessos externa** (cartão 20, opção 1, decisão do Pedro em 2026-10-29). Com Fast 4G e CPU 4x o
LCP da prancheta era de ~2 s no Pages: a página tinha 4,1 MB (668 KB comprimidos), 3,5 MB deles a biblioteca, e a tela só
montava depois de o navegador analisar tudo. Regras:

- O build do site grava `arremessos/<mapa>.js` (`build_tactics_page.biblioteca_js`: a MESMA biblioteca, pelo mesmo
  serializador, entregue por `Prancheta.recebeBiblioteca`) e a página leva só o caminho (`cfg.bibliotecaArquivo`). O
  `build_html` embute por padrão (`biblioteca_externa=False`): os testes e as ferramentas que geram a página sozinha
  continuam iguais.
- A prancheta carrega o arquivo por um `<script>` criado ao fim do `init` (funciona em `file://`, onde `fetch` não
  funciona). Tudo o que liga a granada ao arremesso real espera a biblioteca (`quandoBiblioteca`): o round e o instante do
  Replay nascem iguais aos do modo embutido, mesmo com a biblioteca atrasada. Enquanto ela não chega, "Buscar arremesso
  real" fica desligado com o motivo; se o arquivo não carregar, a prancheta segue sem arremesso real e diz por quê.
- A impressão dos números lê o arquivo e registra a biblioteca com o mesmo nome de antes (`<página>::biblioteca`).
- Medido (local, gzip como o Pages, Fast 4G, CPU 4x): LCP da prancheta de 2,06 / 2,01 s para 0,78 / 0,87 s (375 / 1440);
  a busca de arremesso real fica pronta em 1,4 a 1,55 s (antes, 2,2 a 2,3 s).
