  /* ---------------------------------------------------------------------
     Arquivo: exportar e importar (importar a MESMA tática mescla)
     --------------------------------------------------------------------- */
  function exporta() {
    confirmaGiro();
    gravaAgora();
    var doc = Object.assign({}, S.doc, { versao: FORMATO });
    var blob = new Blob([JSON.stringify(doc, null, 1)], { type: "application/json" });
    var a = el("a", { href: URL.createObjectURL(blob),
                      download: (S.estado.titulo || "tatica").replace(/[^\w\-]+/g, "_") + "." + cfg.mapa + ".json" });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  /** Motivo da recusa, ou "" -- nunca carrega pela metade. */
  function motivoDaRecusa(doc) {
    var erros = problemas(doc, ANDARES.length);
    if (erros.length) return erros.slice(0, 3).join("; ") + (erros.length > 3 ? " (e mais " + (erros.length - 3) + ")" : "");
    if (doc.mapa !== cfg.mapa) return "a tática é de " + doc.mapa + ", e esta prancheta é de " + cfg.mapa;
    if (doc.calibracao !== cfg.radar.calibracao) return "a tática foi feita sobre outra calibração do radar e precisa ser reprojetada";
    return "";
  }

  function importaTexto(texto) {
    var doc;
    try { doc = JSON.parse(texto); } catch (e) { S.aviso = "Arquivo não é JSON."; atualizaAviso(); return false; }
    var erro = motivoDaRecusa(doc);
    if (erro) { S.aviso = "Importação recusada: " + erro + "."; atualizaAviso(); return false; }
    confirmaGiro();
    doc = migra(doc);
    // A cópia local é a da MEMÓRIA quando é a tática aberta: a gravação tem
    // atraso, e mesclar com a do armazém perderia o que acabou de ser feito.
    var local = (S.doc && S.doc.id === doc.id) ? S.doc : Armazem.carrega(doc.id);
    var mesma = S.doc && S.doc.id === doc.id;
    S.doc = local ? mescla(migra(local), doc) : doc;
    if (!mesma) { S.passo = 0; S.t = 0; S.caminho = null; S.pilhaDesfazer = []; S.pilhaRefazer = []; }
    S.sel = null; S.busca = null;
    S.aviso = "";
    reaplica();
    gravaAgora();
    return true;
  }

