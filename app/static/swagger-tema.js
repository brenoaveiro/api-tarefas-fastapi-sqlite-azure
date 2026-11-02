/* Insere a faixa de marca no topo do Swagger (somente DOM estatico; nao altera a interatividade). */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  function cria(tag, attrs) { var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); return e; }
  function monta() {
    if (document.getElementById("ci-faixa")) return;
    var f = document.createElement("div"); f.id = "ci-faixa";
    var svg = cria("svg", { viewBox: "0 0 64 64", "aria-hidden": "true" });
    svg.appendChild(cria("path", { d: "M32 4 8 13v17c0 15 10 25 24 30 14-5 24-15 24-30V13z" }));
    svg.appendChild(cria("path", { d: "M22 32l8 8 14-16", "class": "check" }));
    var t = document.createElement("div");
    var b = document.createElement("b"); b.textContent = "CyberIncident API";
    var s = document.createElement("span"); s.textContent = "SOC Incident Management · Documentação interativa (Swagger)";
    t.appendChild(b); t.appendChild(s);
    var nav = document.createElement("nav");
    [["Dashboard", "/"], ["OpenAPI JSON", "/openapi.json"]].forEach(function (l) {
      var a = document.createElement("a"); a.href = l[1]; a.textContent = l[0]; nav.appendChild(a);
    });
    f.appendChild(svg); f.appendChild(t); f.appendChild(nav);
    document.body.insertBefore(f, document.body.firstChild);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", monta); else monta();
})();
