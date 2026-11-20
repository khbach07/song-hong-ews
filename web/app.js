"use strict";

const byId = id => document.getElementById(id);
const levels = ["Green", "Yellow", "Orange", "Red", "Existing 30+"];
const number = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });
const pct = value => value == null ? "—" : decimal.format(value * 100) + "%";
const count = value => value == null ? "—" : number.format(value);
const metric = value => value == null ? "—" : value.toFixed(4);
const levelClass = level => level === "Existing 30+" ? "existing" : level.toLowerCase();
let meta;
let activeFilters;
let pending;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text != null) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function showError(message) {
  byId("error").textContent = message;
  byId("error").hidden = !message;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Không đọc được dữ liệu");
  return payload;
}

function kpis(id, pairs) {
  byId(id).replaceChildren(...pairs.map(([label, value]) => {
    const card = node("div", null, "kpi");
    card.append(node("span", label), node("strong", value));
    return card;
  }));
}

function table(id, dataset, columns) {
  const wrap = node("div", null, "table-wrap");
  const grid = node("table");
  const heading = grid.createTHead().insertRow();
  for (const [, label] of columns) {
    const cell = node("th", label);
    cell.scope = "col";
    heading.append(cell);
  }
  const body = grid.createTBody();
  for (const row of dataset) {
    const line = body.insertRow();
    for (const [key, , format] of columns) {
      const value = row[key];
      line.insertCell().textContent = format ? format(value) : value ?? "—";
    }
  }
  wrap.append(grid);
  byId(id).replaceChildren(wrap);
}

function detail(loan) {
  byId("detail-title").textContent = loan.app_id;
  const info = node("dl");
  const rows = [
    ["Snapshot", loan.snap_date.slice(0, 7)], ["Cohort / MOB", loan.cohort + " / " + loan.mob],
    ["Cảnh báo", loan.alert_level], ["PD 30+ / 3M", pct(loan.pd_3m)],
    ["DPD hiện tại", loan.dpd_current], ["DPD TB 3 tháng", decimal.format(loan.dpd_mean_3)],
    ["DPD cao nhất 3 tháng", loan.dpd_max_3], ["Tháng trễ trong 3 tháng", loan.late_months_3],
    ["Thay đổi DPD", loan.dpd_delta_1 ?? "Thiếu DPD tháng trước"],
    ["Tín hiệu quan sát", loan.reason], ["Hành động đề xuất", loan.action],
  ];
  for (const [label, value] of rows) info.append(node("dt", label), node("dd", value));
  byId("detail-body").replaceChildren(info);
  byId("detail").showModal();
}

function showSnapshot(snapshot) {
  const tally = level => snapshot.counts[level] || 0;
  kpis("kpis", [
    ["Khoản vay hoạt động", count(snapshot.total)], ["Được chấm PD", count(snapshot.eligible)],
    ["Orange + Red", count(tally("Orange") + tally("Red"))], ["Existing 30+", count(tally("Existing 30+"))],
  ]);
  byId("distribution").replaceChildren(...levels.map(level => {
    const bar = node("span", null, levelClass(level));
    bar.style.width = tally(level) / snapshot.total * 100 + "%";
    return bar;
  }));
  byId("legend").replaceChildren(...levels.map(level => {
    const item = node("button", level + " · " + count(tally(level)), levelClass(level));
    item.setAttribute("aria-pressed", String(activeFilters.get("level") === level));
    item.onclick = () => {
      byId("level").value = activeFilters.get("level") === level ? "" : level;
      applyFilters();
    };
    return item;
  }));
  const body = byId("loans");
  body.replaceChildren();
  for (const loan of snapshot.rows) {
    const row = body.insertRow();
    const link = node("button", loan.app_id, "loan");
    link.onclick = () => detail(loan);
    row.insertCell().append(link);
    for (const value of [loan.cohort, loan.mob, loan.dpd_current, pct(loan.pd_3m)]) {
      row.insertCell().textContent = value;
    }
    row.insertCell().append(node("span", loan.alert_level, "badge " + levelClass(loan.alert_level)));
    row.insertCell().textContent = loan.reason;
  }
  if (!snapshot.rows.length) {
    const cell = body.insertRow().insertCell();
    cell.colSpan = 7;
    cell.textContent = "Không có khoản vay khớp bộ lọc.";
  }
  byId("result-count").textContent = count(snapshot.matched) + " / " + count(snapshot.total) + " khoản vay";
  byId("page").textContent = "Trang " + count(snapshot.page) + " / " + count(snapshot.pages);
  byId("prev").disabled = snapshot.page === 1;
  byId("next").disabled = snapshot.page >= snapshot.pages;
  byId("prev").onclick = () => loadSnapshot(snapshot.page - 1);
  byId("next").onclick = () => loadSnapshot(snapshot.page + 1);
  if (snapshot.matched) {
    byId("export").href = "/api/export?" + activeFilters;
    byId("export").removeAttribute("aria-disabled");
  }
}

async function loadSnapshot(page = 1) {
  pending?.abort();
  const request = new AbortController();
  pending = request;
  const params = new URLSearchParams(activeFilters);
  params.set("page", page);
  showError("");
  byId("result-count").textContent = "Đang tải snapshot…";
  byId("loans").replaceChildren();
  byId("page").textContent = "";
  byId("prev").disabled = byId("next").disabled = true;
  byId("export").removeAttribute("href");
  byId("export").setAttribute("aria-disabled", "true");
  try {
    const data = await fetchJson("/api/snapshot?" + params, { signal: request.signal });
    if (!request.signal.aborted) showSnapshot(data);
  } catch (error) {
    if (!request.signal.aborted) {
      showError(error.message);
      byId("result-count").textContent = "Chưa tải được snapshot.";
      for (const id of ["kpis", "distribution", "legend"]) byId(id).replaceChildren();
    }
  }
}

function applyFilters() {
  activeFilters = new URLSearchParams({
    month: byId("month").value, level: byId("level").value,
    cohort: byId("cohort").value, q: byId("query").value.trim(),
  });
  return loadSnapshot();
}

function drawChart() {
  if (!meta || byId("validation").hidden || !meta.monthly.length) return;
  const canvas = byId("chart");
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const scale = window.devicePixelRatio || 1;
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  const entries = meta.monthly;
  const peak = Math.max(.01, ...entries.flatMap(row => [row.mean_pd, row.event_rate]));
  const max = Math.ceil(peak * 100) / 100;
  const plot = height - 51;
  const step = (width - 65) / entries.length;
  ctx.font = "11px system-ui";
  ctx.fillStyle = "#526679";
  for (let i = 0; i <= 4; i++) {
    const y = 12 + plot * (1 - i / 4);
    ctx.strokeStyle = "#dce5ec";
    ctx.beginPath();
    ctx.moveTo(50, y);
    ctx.lineTo(width - 12, y);
    ctx.stroke();
    ctx.fillText(pct(max * i / 4), 3, y + 4);
  }
  entries.forEach((row, i) => {
    const x = 50 + step * (i + .5);
    const bar = Math.min(14, step / 4);
    for (const [offset, value, color] of [[-bar, row.mean_pd, "#0a705f"], [0, row.event_rate, "#667db0"]]) {
      ctx.fillStyle = color;
      const h = value / max * plot;
      ctx.fillRect(x + offset, 12 + plot - h, bar - 1, h);
    }
    ctx.fillStyle = "#526679";
    ctx.textAlign = "center";
    ctx.fillText(row.month.slice(2), x, height - 15);
    ctx.textAlign = "start";
  });
}

function showReference() {
  const model = meta.models["30"];
  kpis("model-kpis", [
    ["AP mô hình · OOT", metric(model.oot.average_precision)],
    ["AP DPD hiện tại · OOT", metric(model.oot_baseline.average_precision)],
    ["PD bình quân · OOT", pct(model.oot.mean_pd)], ["Tỷ lệ 30+ · OOT", pct(model.oot.event_rate)],
  ]);
  table("monthly", meta.monthly, [
    ["month", "Tháng"], ["snapshots", "Snapshot", count], ["events", "Dương", count],
    ["mean_pd", "PD bình quân", pct], ["event_rate", "Quan sát", pct],
  ]);
  table("capture", model.alert_performance, [
    ["level", "Mức"], ["snapshots", "Snapshot", count], ["events", "Dương", count],
    ["alert_share", "Tỷ trọng", pct], ["event_rate", "Tỷ lệ dương trong mức", pct],
    ["event_capture", "Tỷ lệ bắt dương", pct],
  ]);
  table("thresholds", meta.thresholds, [
    ["level", "Cấp từ ngưỡng"], ["lower_pd", "PD tối thiểu", pct],
    ["target_cumulative_share", "Tỷ trọng mục tiêu", pct],
    ["validation_cumulative_share", "Tỷ trọng validation từ ngưỡng", pct],
  ]);
  table("comparison", meta.comparison, [
    ["model", "Ứng viên"], ["average_precision", "AP", metric],
    ["roc_auc", "ROC-AUC", metric], ["brier", "Brier", metric],
  ]);
  table("calibration", meta.calibration.map((row, i) => ({ ...row, band: i + 1 })), [
    ["band", "Nhóm điểm từ thấp đến cao"], ["snapshots", "Snapshot", count],
    ["mean_pd", "PD bình quân", pct], ["observed_rate", "Quan sát", pct],
  ]);
  table("oot-targets", Object.entries(meta.models).map(([target, result]) => ({
    target: target + "+ / 3M", model: result.champion, ...result.oot,
    baseline: result.oot_baseline.average_precision,
  })), [
    ["target", "Mục tiêu"], ["model", "Mô hình"], ["n", "Snapshot", count],
    ["events", "Dương", count], ["average_precision", "AP", metric], ["baseline", "AP baseline", metric],
    ["roc_auc", "ROC-AUC", metric], ["brier", "Brier", metric],
  ]);
  kpis("scope-kpis", [
    ["Khoản vay trong phạm vi", count(meta.scope.eligible_loans)],
    ["Performance thiếu hồ sơ", count(meta.scope.perf_unmatched_profile)],
    ["Khoản loại theo phạm vi", count(meta.scope.scope_excluded)],
  ]);
  table("label-summary", meta.labels, [
    ["target_type", "Mục tiêu"], ["cohort", "Cohort"], ["status", "Trạng thái"],
    ["snapshots", "Snapshot", count], ["share_pct", "Tỷ trọng", value => pct(value / 100)],
  ]);
  table("inventory", meta.inventory, [
    ["source", "Nguồn"], ["rows", "Số dòng", count], ["unique_app_ids", "Mã duy nhất", count],
    ["match_perf", "Mã khớp với performance", count],
  ]);
  table("missing", meta.missing, [
    ["variable", "Biến"], ["n_total", "Tổng", count],
    ["n_missing", "Thiếu", count], ["pct_missing", "Tỷ lệ thiếu", pct],
  ]);
  table("drift", meta.drift, [
    ["app_ym", "Tháng hồ sơ"], ["n", "Hồ sơ", count], ["pct_missing_income", "Thiếu thu nhập", pct],
    ["median_income", "Trung vị thu nhập (triệu)", v => v == null ? "—" : decimal.format(v)],
  ]);
}

for (const button of document.querySelectorAll("nav button")) {
  button.onclick = () => {
    for (const other of document.querySelectorAll("nav button")) other.removeAttribute("aria-current");
    button.setAttribute("aria-current", "page");
    for (const view of document.querySelectorAll(".view")) view.hidden = view.id !== button.dataset.view;
    drawChart();
  };
}
window.addEventListener("resize", drawChart);
byId("filters").onsubmit = event => {
  event.preventDefault();
  if (meta?.months.length) applyFilters();
};
byId("month").onchange = applyFilters;

async function start() {
  byId("result-count").textContent = "Đang tải danh mục…";
  try {
    meta = await fetchJson("/api/meta");
    for (const level of levels) byId("level").add(new Option(level, level));
    for (const month of [...meta.months].reverse()) byId("month").add(new Option(month, month));
    byId("run-reference").textContent = "Lượt mô hình " + meta.run_id.slice(0, 8);
    if (meta.months.includes(meta.snapshot_month)) byId("month").value = meta.snapshot_month;
    showReference();
    if (!meta.months.length) throw new Error("Nguồn hiện tại chưa có tháng nào đủ điều kiện chấm.");
    byId("month").disabled = false;
    await applyFilters();
    drawChart();
  } catch (error) {
    showError(error.message);
    byId("result-count").textContent = "Chưa tải được danh mục.";
  }
}
start();
