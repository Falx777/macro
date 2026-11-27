let DADOS_CACHE = null;

function tracosComDestaque(datas, valores, nome, cor, modo, destaque, sufixo = "") {
  const traces = [tracoSerie(datas, valores, nome, cor, modo)];
  if (destaque) {
    traces.push({
      x: [destaque.extremo_data],
      y: [destaque.extremo_valor],
      type: "scatter",
      mode: "markers",
      marker: { size: 11, symbol: "star", color: "#f59e0b" },
      name: `Extremo: ${Number(destaque.extremo_valor).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}${sufixo} (${destaque.extremo_data})`,
    });
    traces.push({
      x: [destaque.ultimo_data],
      y: [destaque.ultimo_valor],
      type: "scatter",
      mode: "markers",
      marker: { size: 10, symbol: "diamond", color: "#dc2626" },
      name: `Último: ${Number(destaque.ultimo_valor).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}${sufixo} (${destaque.ultimo_data})`,
    });
  }
  return traces;
}

function renderizarNovosTemas(nt, cfg, modo = "linha") {
  if (!nt) return;

  if (nt.cambio && document.getElementById("g-cambio")) {
    Plotly.newPlot(
      "g-cambio",
      [
        tracoSerie(nt.cambio.datas, nt.cambio.comercial, "Dólar comercial — venda (média)", "#1d4ed8", modo),
        tracoSerie(nt.cambio.datas, nt.cambio.turismo_plot, "Dólar turismo — venda (média)", "#ea580c", modo),
      ],
      {
        title: "Câmbio diário — dólar comercial e turismo para venda",
        yaxis: { title: "R$ por US$" },
        hovermode: "x unified",
      },
      { responsive: true }
    );
  }

  if (nt.deficit_nominal && document.getElementById("g-deficit-nominal")) {
    Plotly.newPlot(
      "g-deficit-nominal",
      tracosComDestaque(
        nt.deficit_nominal.datas,
        nt.deficit_nominal.valores,
        "Resultado nominal orientado como déficit (R$ bi)",
        "#1d4ed8",
        modo,
        nt.deficit_nominal.destaque,
        " bi"
      ),
      {
        title: "NFSP — resultado nominal acumulado em 12 meses (déficit negativo)",
        yaxis: { title: "R$ bilhões nominais", zeroline: true },
        hovermode: "x unified",
      },
      { responsive: true }
    );
  }

  if (nt.divida_bruta && document.getElementById("g-divida-bruta")) {
    Plotly.newPlot(
      "g-divida-bruta",
      tracosComDestaque(
        nt.divida_bruta.datas,
        nt.divida_bruta.valores,
        "DBGG (% do PIB)",
        "#1d4ed8",
        modo,
        nt.divida_bruta.destaque,
        "% do PIB"
      ),
      {
        title: "Dívida bruta do governo geral — metodologia a partir de 2008",
        yaxis: { title: "% do PIB" },
        hovermode: "x unified",
      },
      { responsive: true }
    );
  }

  if (nt.deficit_primario && document.getElementById("g-deficit-primario")) {
    Plotly.newPlot(
      "g-deficit-primario",
      tracosComDestaque(
        nt.deficit_primario.datas,
        nt.deficit_primario.valores,
        "Resultado primário NFSP com sinal invertido (R$ bi)",
        "#1d4ed8",
        modo,
        nt.deficit_primario.destaque,
        " bi"
      ),
      {
        title: "NFSP — resultado primário acumulado em 12 meses (após inversão de sinal)",
        yaxis: { title: "R$ bilhões nominais", zeroline: true },
        hovermode: "x unified",
      },
      { responsive: true }
    );
  }

  if (nt.ibovespa && document.getElementById("g-ibovespa")) {
    Plotly.newPlot(
      "g-ibovespa",
      tracosComDestaque(
        nt.ibovespa.datas,
        nt.ibovespa.valores,
        "Ibovespa — fechamento",
        "#1d4ed8",
        modo,
        nt.ibovespa.destaque,
        " pts"
      ),
      {
        title: "Ibovespa — índice de ações, fechamento diário",
        yaxis: { title: "Pontos do índice" },
        hovermode: "x unified",
      },
      { responsive: true }
    );
  }

  if (nt.volatilidade_ibovespa && document.getElementById("g-volatilidade-ibov")) {
    Plotly.newPlot(
      "g-volatilidade-ibov",
      [
        tracoSerie(
          nt.volatilidade_ibovespa.datas,
          nt.volatilidade_ibovespa.valores,
          "Volatilidade do Ibovespa",
          "#0f766e",
          modo
        ),
      ],
      {
        title: "Volatilidade do índice de ações — Ibovespa",
        yaxis: { title: "Volatilidade" },
        hovermode: "x unified",
      },
      { responsive: true }
    );
  }
}

function tracoSerie(x, y, nome, cor, modo) {
  if (modo === "coluna") {
    return {
      x,
      y,
      name: nome,
      type: "bar",
      marker: cor ? { color: cor } : undefined,
      opacity: 0.82,
    };
  }
  return {
    x,
    y,
    name: nome,
    type: "scatter",
    mode: "lines",
    line: { color: cor || undefined, width: nome === "IPCA geral" ? 2.8 : 1.6 },
  };
}

function marcadoresLayout(cfg, incluirQuebraPnad = false) {
  const shapes = [];
  const annotations = [];

  if (cfg.marcar_eventos && Array.isArray(cfg.eventos)) {
    cfg.eventos.forEach((ev, idx) => {
      shapes.push({
        type: "line",
        x0: ev.data,
        x1: ev.data,
        y0: 0,
        y1: 1,
        yref: "paper",
        line: { color: "#dc2626", width: 1.2, dash: "dot" },
      });
      annotations.push({
        x: ev.data,
        y: 0.96 - (idx % 2) * 0.08,
        yref: "paper",
        text: ev.label,
        textangle: -90,
        xanchor: "right",
        yanchor: "top",
        showarrow: false,
        font: { size: 10, color: "#dc2626" },
      });
    });
  }

  if (incluirQuebraPnad && cfg.marcar_quebra_pnad && Array.isArray(cfg.quebras_pnad)) {
    cfg.quebras_pnad.forEach((q, idx) => {
      shapes.push({
        type: "line",
        x0: q.data,
        x1: q.data,
        y0: 0,
        y1: 1,
        yref: "paper",
        line: { color: "#ea580c", width: 1.2, dash: "dashdot" },
      });
      annotations.push({
        x: q.data,
        y: 0.75 - (idx % 2) * 0.08,
        yref: "paper",
        text: q.label,
        textangle: -90,
        xanchor: "right",
        yanchor: "top",
        showarrow: false,
        font: { size: 10, color: "#ea580c" },
      });
    });
  }

  return { shapes, annotations };
}

function faixaMandatos(cfg, xMin, xMax) {
  if (!cfg.marcar_mandatos_presidentes || !Array.isArray(cfg.mandatos) || !cfg.mandatos.length) {
    return { shapes: [], images: [], annotations: [] };
  }

  const shapes = [];
  const images = [];
  const annotations = [];
  const mandatos = cfg.mandatos;

  for (let i = 0; i < mandatos.length; i++) {
    const ini = mandatos[i].inicio;
    const fim = i + 1 < mandatos.length ? mandatos[i + 1].inicio : xMax;
    const bg = i % 2 === 0 ? "#e5e7eb" : "#f3f4f6";

    // Faixa inferior (-0.24 a -0.05 no eixo y em coordenadas 'domain'/paper)
    shapes.push({
      type: "rect",
      xref: "x",
      yref: "paper",
      x0: ini,
      x1: fim,
      y0: -0.25,
      y1: -0.06,
      fillcolor: bg,
      line: { color: "#ffffff", width: 1 },
    });

    const t0 = new Date(ini).getTime();
    const t1 = new Date(fim).getTime();
    const meio = new Date((t0 + t1) / 2).toISOString().slice(0, 10);

    const fotoSrc = cfg.fotos_b64 && cfg.fotos_b64[mandatos[i].presidente];
    if (fotoSrc) {
      images.push({
        source: fotoSrc,
        xref: "x",
        yref: "paper",
        x: meio,
        y: -0.115,
        sizex: (t1 - t0) * 0.65,
        sizey: 0.085,
        xanchor: "center",
        yanchor: "middle",
        layer: "above",
      });
    }

    annotations.push({
      x: meio,
      y: -0.215,
      xref: "x",
      yref: "paper",
      text: `<b>${mandatos[i].mandato}</b>`,
      showarrow: false,
      xanchor: "center",
      yanchor: "middle",
      font: { size: 10, color: "#1f2937" },
    });
  }

  return { shapes, images, annotations };
}

function tracosColunaAgrupada(datas, seriesObj) {
  return Object.entries(seriesObj || {}).map(([nome, valores]) => ({
    x: datas,
    y: valores,
    name: nome,
    type: "bar",
    opacity: 0.85,
  }));
}

function plotarColunaPib(divId, titulo, yTitulo, datas, seriesObj, zeroline = true) {
  if (!document.getElementById(divId)) return;
  Plotly.newPlot(
    divId,
    tracosColunaAgrupada(datas, seriesObj),
    {
      title: titulo,
      yaxis: { title: yTitulo, zeroline: zeroline },
      barmode: "group",
      hovermode: "x unified",
    },
    { responsive: true }
  );
}

function renderizarPibColunas(pib) {
  if (!pib) return;

  plotarColunaPib(
    "g-pib-qoq-prod",
    "PIB — ótica da produção: variação trimestral",
    "Variação percentual (%)",
    pib.qoq_datas,
    pib.qoq_producao
  );
  plotarColunaPib(
    "g-pib-qoq-desp",
    "PIB — ótica da despesas: variação trimestral",
    "Variação percentual (%)",
    pib.qoq_datas,
    pib.qoq_despesas
  );
  plotarColunaPib(
    "g-pib-yoy-prod",
    "PIB — ótica da produção: variação em 4 trimestres",
    "Variação percentual (%)",
    pib.yoy_datas,
    pib.yoy_producao
  );
  plotarColunaPib(
    "g-pib-yoy-desp",
    "PIB — ótica da despesas: variação em 4 trimestres",
    "Variação percentual (%)",
    pib.yoy_datas,
    pib.yoy_despesas
  );
  plotarColunaPib(
    "g-pib-yoy4-prod",
    "PIB — ótica da produção: últimos quatro trimestres (var. 4 tri)",
    "Variação percentual (%)",
    pib.yoy_recent_datas,
    pib.yoy_recent_producao
  );
  plotarColunaPib(
    "g-pib-yoy4-desp",
    "PIB — ótica da despesas: últimos quatro trimestres (var. 4 tri)",
    "Variação percentual (%)",
    pib.yoy_recent_datas,
    pib.yoy_recent_despesas
  );
  plotarColunaPib(
    "g-pib-part4-prod",
    "PIB — participação da produção (últimos quatro trimestres)",
    "% do VAB",
    pib.part_recent_prod_datas,
    pib.part_recent_producao,
    false
  );
  plotarColunaPib(
    "g-pib-part4-desp",
    "PIB — participação da despesas (últimos quatro trimestres)",
    "% do PIB",
    pib.part_recent_desp_datas,
    pib.part_recent_despesas,
    false
  );
}


// -----------------------------------------------------------------------------
// QUADRO-RESUMO: tabela de indicadores + pizzas do PIB.
// Requer o objeto "resumo" produzido pelo Python e a biblioteca Plotly já carregada.
// No HTML, basta incluir:
// <section class="card"><div id="quadro_resumo" class="chart"></div></section>
// -----------------------------------------------------------------------------
function escaparHTML(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function numeroBR(valor, casas = 2) {
  if (valor === null || valor === undefined || valor === "" || !Number.isFinite(Number(valor))) {
    return "—";
  }
  return Number(valor).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas
  });
}

function dataBR(valor) {
  if (!valor) return "—";
  // Preserva datas ISO e trimestres já formatados (ex.: 2025T4).
  const s = String(valor);
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : escaparHTML(s);
}

function renderizarPizzaResumo(divId, titulo, bloco, unidadeBase) {
  const el = document.getElementById(divId);
  if (!el || !bloco || !Array.isArray(bloco.dados) || !bloco.dados.length) return;

  const labels = bloco.dados.map(x => x.componente);
  const valores = bloco.dados.map(x => Number(x.participacao_pct));
  // Paleta qualitativa consistente para as fatias de composição do PIB.
  const paleta = ["#2878B5", "#2CA02C", "#FF7F0E", "#9467BD", "#17A2B8", "#D64B4B", "#8C9A3C", "#7F7F7F"];
  Plotly.newPlot(divId, [{
    type: "pie",
    labels,
    values: valores,
    texttemplate: "%{percent:.1%}",
    textinfo: "percent",
    textposition: "inside",
    insidetextorientation: "auto",
    textfont: { size: 14, color: "#ffffff", family: "Arial, sans-serif" },
    marker: { colors: labels.map((_, i) => paleta[i % paleta.length]), line: { color: "#ffffff", width: 1.5 } },
    sort: false,
    hovertemplate: "%{label}<br>%{value:.2f}%<extra></extra>"
  }], {
    title: { text: `${titulo}<br><sup>${escaparHTML(bloco.trimestre || "")} — participação sobre ${unidadeBase}</sup>`, x: 0.02, xanchor: "left", font: { size: 19 } },
    showlegend: true,
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.16, yanchor: "top", font: { size: 11 }, itemwidth: 90 },
    margin: { t: 76, b: 95, l: 18, r: 18 },
    height: 390,
    uniformtext: { minsize: 10, mode: "hide" }
  }, { responsive: true, displaylogo: false });
}

function renderizarResumo(resumo) {
  const host = document.getElementById("quadro_resumo");
  if (!host || !resumo) return;

  const linhas = Array.isArray(resumo.tabela) ? resumo.tabela : [];
  const normalizar = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const achar = (termo) => linhas.find(l => normalizar(l.indicador).includes(normalizar(termo)));
  const formatarValor = (l) => {
    if (!l) return "—";
    const unidade = l.unidade || "";
    const casas = unidade === "pontos" ? 0 : 2;
    return `${numeroBR(l.resultado, casas)}${unidade ? ` ${escaparHTML(unidade)}` : ""}`;
  };
  const fonteData = (l) => l ? `<small>${dataBR(l.data)} · ${escaparHTML(l.fonte || "Fonte não informada")}</small>` : "<small>Não disponível</small>";
  const estiloIndicador = (indicador) => {
    const n = normalizar(indicador);
    if (n.includes("selic")) return "background:#ed1c2a;color:#fff";
    if (n.includes("desocupacao") || n.includes("desemprego")) return "background:#75c96b;color:#103b19";
    if (n.includes("dolar") || n.includes("cambio")) {
      if (n.includes("1 semana") || n.includes("seman")) return "background:#0d47a1;color:#fff";
      if (n.includes("1 mes") || n.includes("mens")) return "background:#64b5f6;color:#082b4c";
      return "background:#1976d2;color:#fff";
    }
    if (n.includes("ibovespa") || n.includes("ibov")) {
      if (n.includes("1 semana") || n.includes("seman")) return "background:#e65100;color:#fff";
      if (n.includes("1 mes") || n.includes("mens")) return "background:#ffb74d;color:#4a2500";
      return "background:#ef6c00;color:#fff";
    }
    return "background:#536477;color:#fff";
  };
  const cartaoIndicador = (l, classe = "") => l ? `
    <article class="qr-indicador ${classe}" style="${estiloIndicador(l.indicador)}">
      <div class="qr-indicador-titulo">${escaparHTML(l.indicador)}</div>
      <div class="qr-indicador-valor">${formatarValor(l)}</div>
      ${fonteData(l)}
    </article>` : "";

  const ipca = linhas.filter(l => normalizar(l.indicador).startsWith("ipca") || normalizar(l.indicador).includes("meta de inflacao") || normalizar(l.indicador).includes("desvio do ipca"));
  const pibProd = linhas.filter(l => normalizar(l.indicador).startsWith("pib — producao") || normalizar(l.indicador).startsWith("pib - producao"));
  const pibDesp = linhas.filter(l => normalizar(l.indicador).startsWith("pib — despesas") || normalizar(l.indicador).startsWith("pib - despesas"));
  const usados = new Set([...ipca, ...pibProd, ...pibDesp]);
  const demais = linhas.filter(l => !usados.has(l));

  const blocoTopo = (titulo, classe, itens, destaque) => `
    <section class="qr-bloco ${classe}">
      <header class="qr-bloco-cabecalho"><strong>${titulo}</strong><span>${dataBR(destaque?.data || (itens[0] && itens[0].data))}</span></header>
      <div class="qr-bloco-conteudo">
        ${itens.length ? itens.map(l => `
          <div class="qr-linha">
            <span class="qr-linha-nome">${escaparHTML(l.indicador.replace(/^IPCA\s*[—-]?\s*/i, "").replace(/^PIB\s*[—-]?\s*(produção|despesas)\s*[—-]?\s*/i, ""))}</span>
            <b>${formatarValor(l)}</b>
            <small>${dataBR(l.data)} · ${escaparHTML(l.fonte || "")}</small>
          </div>`).join("") : '<div class="qr-vazio">Dados não disponíveis</div>'}
      </div>
    </section>`;

  const indicadorPrincipal = achar("IPCA — acumulado em 12 meses") || ipca[0];
  const cardsDemais = demais.map(l => cartaoIndicador(l)).join("");
  host.innerHTML = `
    <style>
      #quadro_resumo { width:100%; color:var(--text-color, #172033); }
      #quadro_resumo * { box-sizing:border-box; }
      #quadro_resumo .qr-painel-titulo { margin:0 0 18px; font-size:clamp(20px,2.4vw,28px); font-weight:800; }
      #quadro_resumo .qr-topo { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:18px; align-items:start; }
      #quadro_resumo .qr-bloco { min-width:0; border-radius:18px; overflow:hidden; background:#f4f5f7; box-shadow:0 3px 12px rgba(0,0,0,.08); }
      #quadro_resumo .qr-bloco-cabecalho { min-height:82px; padding:12px 14px 9px; color:#fff; text-align:center; display:flex; flex-direction:column; justify-content:center; border-radius:18px; }
      #quadro_resumo .qr-bloco-cabecalho strong { font-size:clamp(19px,2.1vw,29px); line-height:1.08; text-transform:uppercase; }
      #quadro_resumo .qr-bloco-cabecalho span { font-size:14px; opacity:.9; margin-top:5px; }
      #quadro_resumo .qr-ipca .qr-bloco-cabecalho { background:#20ad50; }
      #quadro_resumo .qr-producao .qr-bloco-cabecalho { background:#ed1c2a; }
      #quadro_resumo .qr-despesas .qr-bloco-cabecalho { background:#079fe0; }
      #quadro_resumo .qr-bloco-conteudo { padding:0 12px 12px; }
      #quadro_resumo .qr-linha { padding:10px 11px; margin-top:8px; background:#858585; color:#fff; border-radius:7px; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:3px 8px; align-items:center; }
      #quadro_resumo .qr-linha:nth-child(even) { background:#b9b9b9; }
      #quadro_resumo .qr-linha-nome { font-weight:700; font-size:14px; overflow-wrap:anywhere; }
      #quadro_resumo .qr-linha b { font-size:15px; white-space:nowrap; }
      #quadro_resumo .qr-linha small { grid-column:1/-1; font-size:10px; line-height:1.35; opacity:.94; overflow-wrap:anywhere; }
      #quadro_resumo .qr-vazio { padding:18px; text-align:center; color:#666; }
      #quadro_resumo .qr-inferior { display:grid; grid-template-columns:minmax(220px,.9fr) minmax(0,2.1fr); gap:24px; margin-top:28px; align-items:start; }
      #quadro_resumo .qr-indicadores { display:grid; gap:12px; }
      #quadro_resumo .qr-indicador { border-radius:15px; padding:12px 15px; color:#fff; background:#ed1c2a; box-shadow:0 3px 10px rgba(0,0,0,.08); }
      #quadro_resumo .qr-indicador-titulo { font-size:15px; font-weight:700; }
      #quadro_resumo .qr-indicador-valor { font-size:25px; line-height:1.15; font-weight:800; }
      #quadro_resumo .qr-indicador small { display:block; margin-top:5px; font-size:10px; line-height:1.35; opacity:.94; overflow-wrap:anywhere; }
      #quadro_resumo .qr-pizzas { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }
      #quadro_resumo .qr-pizza-card { min-width:0; text-align:center; }
      #quadro_resumo .qr-pizza { width:100%; height:390px; min-width:0; }
      #quadro_resumo .qr-fonte-geral { margin-top:16px; font-size:10px; opacity:.7; }
      @media(max-width:850px) { #quadro_resumo .qr-topo { grid-template-columns:1fr; } #quadro_resumo .qr-inferior { grid-template-columns:1fr; } }
      @media(max-width:560px) { #quadro_resumo .qr-pizzas { grid-template-columns:1fr; } #quadro_resumo .qr-pizza { height:370px; } }
    </style>
    <h3 class="qr-painel-titulo">Painel-resumo da economia brasileira</h3>
    <div class="qr-topo">
      ${blocoTopo("IPCA", "qr-ipca", ipca, indicadorPrincipal)}
      ${blocoTopo("PIB produção", "qr-producao", pibProd)}
      ${blocoTopo("PIB despesas", "qr-despesas", pibDesp)}
    </div>
    <div class="qr-inferior">
      <section class="qr-indicadores">${cardsDemais || '<div class="qr-vazio">Indicadores complementares não disponíveis</div>'}</section>
      <section class="qr-pizzas">
        <div class="qr-pizza-card"><div id="quadro_resumo_pizza_producao" class="qr-pizza"></div></div>
        <div class="qr-pizza-card"><div id="quadro_resumo_pizza_despesas" class="qr-pizza"></div></div>
      </section>
    </div>
    <div class="qr-fonte-geral">Atualização do arquivo: ${escaparHTML(resumo.gerado_em_utc || "—")}. As datas e fontes específicas aparecem em cada indicador.</div>
  `;

  const pizzas = resumo.graficos_pizza || {};
  renderizarPizzaResumo("quadro_resumo_pizza_producao", "Composição do PIB — produção", pizzas.producao, "valor adicionado a preços básicos");
  renderizarPizzaResumo("quadro_resumo_pizza_despesas", "Composição do PIB — despesas", pizzas.despesas, "PIB a preços de mercado");
}

function renderizarTodos(modo = "linha") {
  if (!DADOS_CACHE) return;
  const d = DADOS_CACHE;
  const cfg = d.config;

  // 1. IPCA componentes (12m)
  const tracesIpcaComp = Object.entries(d.ipca_componentes).map(([nome, s]) =>
    tracoSerie(s.datas, s.valores, nome, nome === "IPCA geral" ? "#111827" : undefined, modo)
  );
  Plotly.newPlot(
    "g-ipca-comp",
    tracesIpcaComp,
    {
      title: "IPCA acumulado em 12 meses — índice geral e componentes",
      yaxis: { title: "% acumulado em 12 meses" },
      hovermode: "x unified",
    },
    { responsive: true }
  );

  // 2. IPCA observado, meta e banda + expectativa BCB
  const m = d.ipca_meta;
  const tracesMeta = [
    tracoSerie(m.datas, m.ipca_12m, "IPCA observado (12m)", "#1f2937", modo),
    tracoSerie(m.datas, m.meta_pct, "Meta anual", "#2563eb", modo),
    {
      x: m.datas,
      y: m.limite_superior,
      type: "scatter",
      mode: "lines",
      line: { width: 0 },
      showlegend: false,
      hoverinfo: "skip",
    },
    {
      x: m.datas,
      y: m.limite_inferior,
      type: "scatter",
      mode: "lines",
      fill: "tonexty",
      fillcolor: "rgba(147, 197, 253, 0.25)",
      line: { width: 0 },
      name: "Banda configurada",
    },
  ];
  if (m.expectativa) {
    tracesMeta.push({
      x: [m.expectativa.data],
      y: [m.expectativa.media],
      type: "scatter",
      mode: "markers+text",
      marker: { size: 10, color: "#dc2626" },
      text: [`${m.expectativa.media.toFixed(2)}%`],
      textposition: "top right",
      name: `Consenso BCB IPCA (${m.expectativa.ano_referencia})`,
    });
  }
  Plotly.newPlot(
    "g-ipca-meta",
    tracesMeta,
    {
      title: "IPCA observado, meta e última expectativa anual disponível no BCB",
      yaxis: { title: "% a.a. / acumulado em 12 meses" },
      hovermode: "x unified",
    },
    { responsive: true }
  );

  // 3. Selic efetiva + expectativa + mandatos
  const s = d.selic;
  const ultimoSelic = s.valores[s.valores.length - 1];
  const ultimaDataSelic = s.datas[s.datas.length - 1];
  const tracesSelic = [
    tracoSerie(s.datas, s.valores, "Meta Selic efetiva", "#1d4ed8", modo),
    {
      x: [ultimaDataSelic],
      y: [ultimoSelic],
      type: "scatter",
      mode: "markers",
      marker: { size: 10, color: "#dc2626" },
      name: `Última taxa: ${Number(ultimoSelic).toFixed(2)}% (${ultimaDataSelic})`,
    },
  ];
  if (s.expectativa) {
    tracesSelic.push({
      x: [s.expectativa.data],
      y: [s.expectativa.media],
      type: "scatter",
      mode: "markers",
      marker: { size: 10, symbol: "diamond", color: "#f59e0b" },
      name: `Última expectativa Selic (${s.expectativa.ano_referencia}): ${s.expectativa.media.toFixed(2)}%`,
    });
  }
  const mSelic = marcadoresLayout(cfg, false);
  const fSelic = faixaMandatos(cfg, s.datas[0], ultimaDataSelic);
  Plotly.newPlot(
    "g-selic",
    tracesSelic,
    {
      title: "Selic e expectativas — Mandatos dos presidentes do Brasil",
      yaxis: { title: "% ao ano" },
      margin: { b: 130 },
      shapes: [...mSelic.shapes, ...fSelic.shapes],
      images: fSelic.images,
      annotations: [...mSelic.annotations, ...fSelic.annotations],
      hovermode: "x unified",
    },
    { responsive: true }
  );

  // 4. Desemprego (PNAD Contínua) + quebra PNAD + mandatos
  const des = d.desemprego;
  const mDes = marcadoresLayout(cfg, true);
  const fDes = faixaMandatos(cfg, des.datas[0], des.datas[des.datas.length - 1]);
  Plotly.newPlot(
    "g-desemprego",
    [tracoSerie(des.datas, des.valores, "Taxa de desocupação", "#0f766e", modo)],
    {
      title: "Taxa de desocupação — PNAD Contínua",
      yaxis: { title: "%" },
      margin: { b: 130 },
      shapes: [...mDes.shapes, ...fDes.shapes],
      images: fDes.images,
      annotations: [...mDes.annotations, ...fDes.annotations],
      hovermode: "x unified",
    },
    { responsive: true }
  );

  // 5. Gráficos trimestrais do PIB (SIDRA 1621 e 6613) em coluna
  renderizarPibColunas(d.pib);
 // 6. grafico das estatisticas fiscais, cambio e ibovespa
  renderizarNovosTemas(d.novos_temas, cfg, modo);  
  renderizarResumo(d.resumo);

}

async function iniciar() {
  const resp = await fetch(`dados/macro_dados.json?v=${Date.now()}`);
  DADOS_CACHE = await resp.json();
  document.getElementById("atualizacao").textContent = DADOS_CACHE.gerado_em_utc;
  renderizarTodos("linha");
}

iniciar();
