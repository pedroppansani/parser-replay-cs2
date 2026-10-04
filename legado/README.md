# legado/

Código que **não é mais usado** e fica só como registro.

- `app.py` e `theme.py`: o primeiro dashboard, em Streamlit. Foi substituído pelas páginas
  estáticas autocontidas (`scripts/build_web_page.py`, `scripts/build_site.py`), que abrem como
  arquivo local e são o que o site publica. Saiu de `dashboard/` na auditoria (item 5.6, 2026-10-03)
  e suas dependências (Streamlit, Plotly) saíram dos `requirements`.

Para rodar mesmo assim: `py -3.12 -m pip install streamlit==1.64.0 plotly==7.1.0` e
`py -3.12 -m streamlit run legado/app.py`. Nada no pipeline, nos testes ou no CI depende dele.
