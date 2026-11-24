let DADOS_CACHE = null;

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
}

async function iniciar() {
  const resp = await fetch(`dados/macro_dados.json?v=${Date.now()}`);
  DADOS_CACHE = await resp.json();
  document.getElementById("atualizacao").textContent = DADOS_CACHE.gerado_em_utc;
  renderizarTodos("linha");
}

iniciar();
