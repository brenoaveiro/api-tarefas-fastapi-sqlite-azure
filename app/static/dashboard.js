(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var SEVS = ["critica", "alta", "media", "baixa"];
  var ROT = { critica: "Critica", alta: "Alta", media: "Media", baixa: "Baixa" };

  // Sempre textContent: dados vindos do banco nunca sao interpretados como HTML (protecao contra XSS).
  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt !== undefined) n.textContent = txt;
    return n;
  }
  function get(url) {
    return fetch(url, { headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }
  function fmt(iso) { return iso ? iso.replace("T", " ").slice(0, 16) : "-"; }
  function rotulo(s) { return String(s).replace(/_/g, " "); }

  function saude() {
    return get("/health").then(function (h) {
      var ok = h.status === "ok";
      $("saude").className = "saude " + (ok ? "on" : "off");
      $("saude-txt").textContent = ok ? "API online · banco " + h.database + " · v" + h.version : "API degradada";
    }).catch(function () {
      $("saude").className = "saude off";
      $("saude-txt").textContent = "API indisponivel";
    });
  }

  function indicadores(e) {
    $("k-total").textContent = e.total;
    $("k-criticos").textContent = e.por_severidade.critica;
    $("k-abertos").textContent = e.por_status.aberto;
    $("k-resolvidos").textContent = e.por_status.resolvido;
    var g = $("grafico"), max = Math.max(1, e.total);
    g.textContent = "";
    SEVS.forEach(function (s) {
      var n = e.por_severidade[s], linha = el("div", "barra sev-" + s), tr = el("div", "trilho"), p = el("div", "preench");
      p.style.width = Math.round((n / max) * 100) + "%";
      tr.appendChild(p);
      linha.appendChild(el("span", "rot", ROT[s]));
      linha.appendChild(tr);
      linha.appendChild(el("span", "val", String(n)));
      g.appendChild(linha);
    });
  }

  function tabela(d) {
    var tb = $("tabela");
    tb.textContent = "";
    if (!d.items.length) {
      var tr0 = el("tr"), td0 = el("td", "vazio", "Nenhum incidente cadastrado.");
      td0.colSpan = 6; tr0.appendChild(td0); tb.appendChild(tr0); return;
    }
    d.items.forEach(function (i) {
      var tr = el("tr");
      tr.appendChild(el("td", "", "#" + i.id));
      tr.appendChild(el("td", "tit", i.titulo));
      tr.appendChild(el("td", "", rotulo(i.categoria)));
      var ts = el("td"); ts.appendChild(el("span", "badge sev-" + i.severidade, ROT[i.severidade] || i.severidade)); tr.appendChild(ts);
      var tt = el("td"); tt.appendChild(el("span", "badge st-" + i.status, rotulo(i.status))); tr.appendChild(tt);
      tr.appendChild(el("td", "", fmt(i.criado_em)));
      tb.appendChild(tr);
    });
  }

  function erro() {
    var tb = $("tabela"); tb.textContent = "";
    var tr = el("tr"), td = el("td", "vazio", "Nao foi possivel carregar os dados.");
    td.colSpan = 6; tr.appendChild(td); tb.appendChild(tr);
  }

  function carregar() {
    saude();
    get("/incidentes/estatisticas").then(indicadores).catch(erro);
    get("/incidentes?limit=10").then(tabela).catch(erro);
  }
  carregar();
  setInterval(carregar, 30000);
})();
