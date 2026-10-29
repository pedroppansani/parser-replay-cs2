  /* ---------------------------------------------------------------------
     Armazem -- a interface de persistência. A página só fala com isto.
     Contrato:
       lista(mapa)  -> [{id, titulo, atualizada_em, autores}]  (mais recente primeiro)
       carrega(id)  -> documento ou null
       grava(doc)   -> true se gravou
       apaga(id)    -> true se apagou
     --------------------------------------------------------------------- */
  function ArmazemDoNavegador(prefixo) {
    // o acesso seguro (try/catch em tudo) é o do MapCore, o mesmo da anotação
    var A = MapCore.criaArmazem();
    function le(chave) { return MapCore.lerJson(A.le("localStorage", prefixo + chave)); }
    function escreve(chave, valor) { return A.grava("localStorage", prefixo + chave, JSON.stringify(valor)); }
    function indice() { return le("indice") || {}; }
    return {
      tipo: "navegador",
      lista: function (mapa) {
        var ind = indice();
        return Object.keys(ind).map(function (id) { return ind[id]; })
          .filter(function (r) { return r.mapa === mapa; })
          .sort(function (a, b) { return a.atualizada_em < b.atualizada_em ? 1 : -1; });
      },
      carrega: function (id) { return le("tatica:" + id); },
      grava: function (doc) {
        if (!escreve("tatica:" + doc.id, doc)) return false;
        var ind = indice(), est = aplica(doc.operacoes);
        var autores = {};
        doc.operacoes.forEach(function (op) { autores[op.autor] = true; });
        ind[doc.id] = { id: doc.id, mapa: doc.mapa, titulo: est.titulo || "(sem título)",
                        atualizada_em: agora(), autores: Object.keys(autores).sort() };
        return escreve("indice", ind);
      },
      apaga: function (id) {
        if (!A.remove("localStorage", prefixo + "tatica:" + id)) return false;
        var ind = indice(); delete ind[id];
        return escreve("indice", ind);
      },
      // a tática guardada que a validação recusou (B-1): vai para uma chave à parte, para não se perder em silêncio
      recusa: function (id, doc) {
        if (!escreve("tatica:" + id + ":recusada", doc)) return false;
        A.remove("localStorage", prefixo + "tatica:" + id);
        var ind = indice(); delete ind[id];
        escreve("indice", ind);
        return true;
      },
      autor: function (novo) {
        if (novo !== undefined) escreve("autor", novo);
        return le("autor");
      },
      // a tática ABERTA nesta aba (sessão): recarregar volta nela; outra aba
      // ou "Criar tática" começam limpas
      aberta: function (mapa, id) {
        if (id !== undefined) A.grava("sessionStorage", prefixo + "aberta:" + mapa, id);
        return A.le("sessionStorage", prefixo + "aberta:" + mapa);
      }
    };
  }

