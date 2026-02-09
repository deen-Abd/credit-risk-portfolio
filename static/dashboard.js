let chartRegion, chartRating, chartTrend;

function formatMoneyM(x) {
  // x already in "millions"
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(x) + "m";
}
function formatPct(x) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(x) + "%";
}

async function loadData() {
  const res = await fetch("/api/portfolio");
  if (!res.ok) throw new Error("Failed to load /api/portfolio");
  return res.json();
}

function setKpis(kpis, asof) {
  document.getElementById("asof").textContent = `As of ${asof}`;
  document.getElementById("kpi-exposure").textContent = formatMoneyM(kpis.total_exposure_m);
  document.getElementById("kpi-el").textContent = formatMoneyM(kpis.total_expected_loss_m);
  document.getElementById("kpi-pd").textContent = formatPct(kpis.avg_pd_pct);
  document.getElementById("kpi-lgd").textContent = formatPct(kpis.avg_lgd_pct);
  document.getElementById("kpi-n").textContent = kpis.counterparties.toString();
}

function buildTable(rows) {
  const tbody = document.querySelector("#top10 tbody");
  tbody.innerHTML = "";

  for (const r of rows) {
    const tr = document.createElement("tr");

    const cols = [
      r.counterparty,
      r.region,
      r.industry,
      r.rating,
      r.credit_limit_m.toFixed(2),
      r.utilization_pct.toFixed(1) + "%",
      r.ead_m.toFixed(2),
      r.pd_pct.toFixed(2) + "%",
      r.lgd_pct.toFixed(1) + "%",
      r.expected_loss_m.toFixed(3),
      r.dpd.toString()
    ];

    cols.forEach((c, idx) => {
      const td = document.createElement("td");
      td.textContent = c;
      if (idx >= 4) td.classList.add("num");
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  }
}

function buildBarChart(canvasId, labels, values, label) {
  const ctx = document.getElementById(canvasId);
  return new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label, data: values }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${label}: ${formatMoneyM(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        y: {
          ticks: {
            callback: (v) => formatMoneyM(v)
          }
        }
      }
    }
  });
}

function buildLineChart(canvasId, labels, values, label) {
  const ctx = document.getElementById(canvasId);
  return new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{ label, data: values, tension: 0.25 }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${label}: ${formatMoneyM(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        y: {
          ticks: { callback: (v) => formatMoneyM(v) }
        }
      }
    }
  });
}

function renderCharts(charts) {
  // destroy if re-render
  if (chartRegion) chartRegion.destroy();
  if (chartRating) chartRating.destroy();
  if (chartTrend) chartTrend.destroy();

  chartRegion = buildBarChart(
    "chart-region",
    charts.exposure_by_region.labels,
    charts.exposure_by_region.values,
    "Exposure"
  );

  chartRating = buildBarChart(
    "chart-rating",
    charts.expected_loss_by_rating.labels,
    charts.expected_loss_by_rating.values,
    "Expected Loss"
  );

  chartTrend = buildLineChart(
    "chart-trend",
    charts.monthly_el_trend.labels,
    charts.monthly_el_trend.values,
    "Portfolio EL"
  );
}

(async function init() {
  try {
    const data = await loadData();
    setKpis(data.kpis, data.asof);
    renderCharts(data.charts);
    buildTable(data.top10);
  } catch (e) {
    console.error(e);
    alert("Could not load dashboard data. Check the Flask server console.");
  }
})();
