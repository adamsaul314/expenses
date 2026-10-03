/* Expenses dashboard — vanilla JS, no build step. */
"use strict";

const PALETTE = [
  "#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#475569",
];

const eur = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR" });

const el = (id) => document.getElementById(id);
const money = (value) => eur.format(Number(value || 0));

let months = [];
let current = null;
let donutChart = null;
let trendChart = null;

async function api(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function setStatus(message, isError = false) {
  const status = el("status");
  status.textContent = message;
  status.classList.toggle("error", isError);
  status.hidden = !message;
}

function showDashboard(show) {
  el("dashboard").hidden = !show;
}

async function loadMonths() {
  const data = await api("/api/months");
  months = data.months || [];

  const select = el("month-select");
  select.innerHTML = "";
  if (!months.length) {
    showDashboard(false);
    setStatus("No statements found yet. Add a CSV to the statements folder or run `make fetch`.");
    return false;
  }

  for (const entry of months) {
    const option = document.createElement("option");
    option.value = entry.month;
    option.textContent = entry.month;
    select.appendChild(option);
  }
  select.value = months[0].month;
  return true;
}

async function loadMonth(month) {
  setStatus("Loading…");
  try {
    const data = await api(`/api/months/${encodeURIComponent(month)}`);
    current = data;
    showDashboard(true);
    setStatus("");
    renderCards(data.report);
    renderDonut(data.report.categories || []);
    renderMerchants(data.report.top_merchants || []);
    renderTransactions(data.transactions || []);
    renderNotes(data.report);
  } catch (error) {
    showDashboard(false);
    setStatus(`Could not load ${month}: ${error.message}`, true);
  }
}

function renderCards(report) {
  el("card-spend").textContent = money(report.total_spend);
  el("card-count").textContent = report.transaction_count ?? 0;
  const top = (report.categories || [])[0];
  el("card-top").textContent = top ? top.category : "—";
  el("card-inflow").textContent = money(report.total_inflow);
}

function renderDonut(categories) {
  const canvas = el("donut");
  if (donutChart) donutChart.destroy();
  if (!categories.length) return;

  donutChart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: categories.map((c) => c.category),
      datasets: [{
        data: categories.map((c) => Number(c.total)),
        backgroundColor: categories.map((_, i) => PALETTE[i % PALETTE.length]),
        borderWidth: 0,
        hoverOffset: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 10, padding: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0) || 1;
              const share = ((ctx.parsed / total) * 100).toFixed(1);
              return ` ${ctx.label}: ${money(ctx.parsed)} (${share}%)`;
            },
          },
        },
      },
    },
  });
}

function renderTrend() {
  const canvas = el("trend");
  if (trendChart) trendChart.destroy();
  if (!months.length) return;

  const ordered = [...months].sort((a, b) => a.month.localeCompare(b.month));
  trendChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: ordered.map((m) => m.month),
      datasets: [{
        label: "Spend",
        data: ordered.map((m) => Number(m.total_spend)),
        backgroundColor: "#2563eb",
        borderRadius: 6,
        maxBarThickness: 44,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ` ${money(ctx.parsed.y)}` } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { callback: (v) => "€" + v } },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderMerchants(merchants) {
  const body = el("merchant-table").querySelector("tbody");
  body.innerHTML = "";
  for (const merchant of merchants) {
    const row = body.insertRow();
    row.insertCell().textContent = merchant.merchant;
    const count = row.insertCell();
    count.className = "num";
    count.textContent = merchant.count;
    const total = row.insertCell();
    total.className = "num";
    total.textContent = money(merchant.total);
  }
}

function renderTransactions(transactions) {
  const filter = el("category-filter");
  const categories = [...new Set(transactions.map((t) => t.category))].sort();
  filter.innerHTML = '<option value="">All categories</option>';
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    filter.appendChild(option);
  }
  el("search").value = "";
  filter.value = "";
  drawTransactions(transactions);
}

function drawTransactions(transactions) {
  const term = el("search").value.trim().toLowerCase();
  const category = el("category-filter").value;
  const body = el("tx-table").querySelector("tbody");
  body.innerHTML = "";

  const rows = transactions.filter((tx) => {
    const matchesTerm = !term || tx.description.toLowerCase().includes(term);
    const matchesCategory = !category || tx.category === category;
    return matchesTerm && matchesCategory;
  });

  if (!rows.length) {
    const row = body.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 4;
    cell.textContent = "No matching transactions.";
    cell.style.color = "var(--muted)";
    return;
  }

  for (const tx of rows) {
    const row = body.insertRow();
    row.insertCell().textContent = tx.date || "—";
    const desc = row.insertCell();
    desc.className = "desc";
    desc.textContent = tx.description || "(no description)";
    const cat = row.insertCell();
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = tx.category;
    cat.appendChild(pill);
    const amount = row.insertCell();
    amount.className = "num";
    amount.textContent = money(tx.amount);
    amount.classList.add(Number(tx.amount) < 0 ? "amount-neg" : "amount-pos");
  }
}

function renderNotes(report) {
  const panel = el("notes-panel");
  const lines = [];
  if (report.non_eur && report.non_eur.length) {
    lines.push(`${report.non_eur.length} non-EUR transaction(s) excluded from totals.`);
  }
  const uncategorized = (report.categories || []).find((c) => c.category === "Uncategorized");
  if (uncategorized) {
    lines.push(`${uncategorized.count} uncategorized transaction(s) worth ${money(uncategorized.total)} — consider adding keywords.`);
  }
  if (!lines.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  panel.innerHTML = "<h2>Notes</h2><ul class=\"notes-list\"></ul>";
  const list = panel.querySelector("ul");
  for (const line of lines) {
    const item = document.createElement("li");
    item.textContent = line;
    list.appendChild(item);
  }
}

async function refresh() {
  const ok = await loadMonths();
  if (ok) {
    renderTrend();
    await loadMonth(el("month-select").value);
  }
}

el("month-select").addEventListener("change", (event) => loadMonth(event.target.value));
el("refresh").addEventListener("click", refresh);
el("search").addEventListener("input", () => current && drawTransactions(current.transactions || []));
el("category-filter").addEventListener("change", () => current && drawTransactions(current.transactions || []));

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}

refresh().catch((error) => setStatus(`Something went wrong: ${error.message}`, true));
