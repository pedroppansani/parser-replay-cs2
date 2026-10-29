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

**Medidas da prancheta da Mirage** (Fast 4G, CPU 4x, 5 medidas por largura, cache limpo; LCP mediano, o pior entre parênteses):

| onde | versão | LCP a 375 | LCP a 1440 | CLS | busca de arremesso real pronta |
|---|---|---|---|---|---|
| local, gzip como o Pages | antes (`b54a5240`) | 2,06 s (2,31) | 2,01 s (2,20) | 0 | 2,2 a 2,3 s |
| local, gzip como o Pages | depois (branch do cartão 20) | 0,78 s (0,83) | 0,87 s (0,92) | 0 | 1,4 a 1,55 s |
| Pages | antes (`73fc57d0`, v2-7) | 2,02 s (2,44) | 2,04 s (2,47) | 0 | -- |
| Pages | depois (`24eea71e`, 2026-10-29) | 0,89 s (2,41) | 0,78 s (0,80) | 0 | -- |

No Pages, uma das 5 medidas a 375 deu 2,41 s (provavelmente o primeiro pedido do arquivo novo ao CDN); a mediana não muda.
