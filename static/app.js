"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let activeReturnCheckoutId = null;

// Reports state
const reportCharts = {};       // keyed by canvas id; holds Chart instances for destroy/re-create
let reportsInitialized = false;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupScanInput();
  setupRegisterModal();
  setupCheckoutModal();
  setupReturnModal();
  setupModalCloseButtons();
  setupOverlayDismiss();
  loadAttendance();
  focusScanInput();
});

// ── Focus management ──────────────────────────────────────────────────────────
function focusScanInput() {
  if (!anyModalOpen()) {
    const el = document.getElementById("scan-input");
    if (el) el.focus();
  }
}

function anyModalOpen() {
  return [...document.querySelectorAll(".modal-overlay")]
    .some(m => !m.classList.contains("hidden"));
}

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
  if (!anyModalOpen()) focusScanInput();
}

function closeAllModals() {
  document.querySelectorAll(".modal-overlay").forEach(m => m.classList.add("hidden"));
  focusScanInput();
}

// Close modals on Escape
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeAllModals();
});

// Close on overlay background click
function setupOverlayDismiss() {
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", e => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });
}

// Wire up [data-close] buttons
function setupModalCloseButtons() {
  document.querySelectorAll("[data-close]").forEach(btn => {
    btn.addEventListener("click", () => closeModal(btn.dataset.close));
  });
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
      btn.classList.add("active");
      const panel = document.getElementById(`tab-${btn.dataset.tab}`);
      if (panel) panel.classList.remove("hidden");
      if (btn.dataset.tab === "gear") {
        loadGearTab();
      } else if (btn.dataset.tab === "reports") {
        initReportsTab();
      } else {
        focusScanInput();
      }
    });
  });
}

// ── Attendance scan ───────────────────────────────────────────────────────────
function setupScanInput() {
  const input = document.getElementById("scan-input");
  input.addEventListener("keydown", async e => {
    if (e.key !== "Enter") return;
    const code = input.value.trim();
    if (!code) return;
    input.value = "";

    try {
      const res = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scanner_code: code }),
      });
      const data = await res.json();
      appendScanLog(data);
      loadAttendance();
    } catch {
      appendScanLogRaw("Error communicating with server", false);
    }
  });
}

function appendScanLog(data) {
  const msg = data.registered
    ? `[${data.time}]  Welcome, ${data.name}!`
    : `[${data.time}]  Unknown scan (not registered)`;
  appendScanLogRaw(msg, data.registered);
}

function appendScanLogRaw(msg, registered) {
  const list = document.getElementById("scan-log-list");
  // Remove empty-state placeholder on first real entry
  const placeholder = list.querySelector(".empty-state");
  if (placeholder) placeholder.remove();

  const li = document.createElement("li");
  li.textContent = msg;
  li.className = registered ? "log-entry-registered" : "log-entry-unknown";
  list.prepend(li);
}

async function loadAttendance() {
  try {
    const res = await fetch("/api/attendance/today");
    const data = await res.json();
    document.getElementById("attendance-count").textContent = data.count;
  } catch {
    // Non-critical; don't surface to user
  }
}

// ── Register Student modal ────────────────────────────────────────────────────
function setupRegisterModal() {
  document.getElementById("btn-register-open").addEventListener("click", () => {
    clearRegisterForm();
    openModal("modal-register");
    document.getElementById("reg-name").focus();
  });

  document.getElementById("btn-register-submit").addEventListener("click", submitRegister);

  // Allow Enter on any field to submit
  ["reg-name", "reg-csu-id", "reg-scan-id", "reg-major", "reg-grade"].forEach(id => {
    document.getElementById(id).addEventListener("keydown", e => {
      if (e.key === "Enter") submitRegister();
    });
  });
}

function clearRegisterForm() {
  ["reg-name", "reg-csu-id", "reg-scan-id", "reg-major"].forEach(id => {
    document.getElementById(id).value = "";
  });
  document.getElementById("reg-grade").value = "";
  showError("reg-error", null);
}

async function submitRegister() {
  const body = {
    full_name:    document.getElementById("reg-name").value.trim(),
    school_id:    document.getElementById("reg-csu-id").value.trim(),
    scanner_code: document.getElementById("reg-scan-id").value.trim(),
    major:        document.getElementById("reg-major").value.trim(),
    grade_level:  document.getElementById("reg-grade").value,
  };

  if (!body.full_name) { showError("reg-error", "Full name is required."); document.getElementById("reg-name").focus(); return; }
  if (!body.school_id) { showError("reg-error", "CSU ID is required."); document.getElementById("reg-csu-id").focus(); return; }
  if (!body.scanner_code) { showError("reg-error", "Scan ID is required."); document.getElementById("reg-scan-id").focus(); return; }
  if (!body.major) { showError("reg-error", "Major is required."); document.getElementById("reg-major").focus(); return; }

  try {
    const res = await fetch("/api/students/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.status === 201) {
      closeModal("modal-register");
    } else {
      const err = await res.json();
      showError("reg-error", err.error || "Registration failed.");
      document.getElementById("reg-scan-id").focus();
    }
  } catch {
    showError("reg-error", "Error communicating with server.");
  }
}

// ── Gear Checkout modal ───────────────────────────────────────────────────────
function setupCheckoutModal() {
  document.getElementById("btn-checkout-open").addEventListener("click", () => {
    clearCheckoutForm();
    openModal("modal-checkout");
    document.getElementById("checkout-scan-input").focus();
  });

  const scanInput = document.getElementById("checkout-scan-input");
  scanInput.addEventListener("keydown", async e => {
    if (e.key !== "Enter") return;
    await submitCheckout();
  });

  document.getElementById("btn-checkout-submit").addEventListener("click", submitCheckout);
}

function clearCheckoutForm() {
  ["chk-keyboard", "chk-mouse", "chk-mousepad", "chk-headset"].forEach(id => {
    document.getElementById(id).checked = false;
  });
  document.getElementById("checkout-scan-input").value = "";
  showError("checkout-error", null);
}

async function submitCheckout() {
  const keyboard  = document.getElementById("chk-keyboard").checked;
  const mouse     = document.getElementById("chk-mouse").checked;
  const mousepad  = document.getElementById("chk-mousepad").checked;
  const headset   = document.getElementById("chk-headset").checked;
  const code      = document.getElementById("checkout-scan-input").value.trim();

  if (!keyboard && !mouse && !mousepad && !headset) {
    showError("checkout-error", "Select at least one gear item.");
    return;
  }
  if (!code) {
    showError("checkout-error", "Scan the student's ID.");
    document.getElementById("checkout-scan-input").focus();
    return;
  }

  try {
    const res = await fetch("/api/gear/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scanner_code: code, keyboard, mouse, mousepad, headset }),
    });
    if (res.status === 201) {
      closeModal("modal-checkout");
      loadGearTab();
    } else {
      const err = await res.json();
      showError("checkout-error", err.error || "Checkout failed.");
      document.getElementById("checkout-scan-input").value = "";
      document.getElementById("checkout-scan-input").focus();
    }
  } catch {
    showError("checkout-error", "Error communicating with server.");
  }
}

// ── Return Gear modal ─────────────────────────────────────────────────────────
function setupReturnModal() {
  const scanInput = document.getElementById("return-scan-input");
  scanInput.addEventListener("keydown", async e => {
    if (e.key !== "Enter") return;
    await submitReturn();
  });

  document.getElementById("btn-return-submit").addEventListener("click", submitReturn);
}

function openReturnModal(checkoutId, studentName, items) {
  activeReturnCheckoutId = checkoutId;
  document.getElementById("return-student-info").textContent =
    `Returning ${items.join(", ")} for ${studentName}.`;
  document.getElementById("return-scan-input").value = "";
  showError("return-error", null);
  openModal("modal-return");
  document.getElementById("return-scan-input").focus();
}

async function submitReturn() {
  const code = document.getElementById("return-scan-input").value.trim();
  if (!code) {
    showError("return-error", "Please scan the student's ID.");
    return;
  }

  try {
    const res = await fetch(`/api/gear/return/${activeReturnCheckoutId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scanner_code: code }),
    });
    if (res.ok) {
      activeReturnCheckoutId = null;
      closeModal("modal-return");
      loadGearTab();
    } else {
      const err = await res.json();
      showError("return-error", err.error || "Return failed.");
      document.getElementById("return-scan-input").value = "";
      document.getElementById("return-scan-input").focus();
    }
  } catch {
    showError("return-error", "Error communicating with server.");
  }
}

// ── Gear tab data ─────────────────────────────────────────────────────────────
async function loadGearTab() {
  try {
    const [statsRes, checkoutsRes] = await Promise.all([
      fetch("/api/gear/stats"),
      fetch("/api/gear/checkouts"),
    ]);
    const stats     = await statsRes.json();
    const checkouts = await checkoutsRes.json();

    document.getElementById("stat-total").textContent     = stats.total;
    document.getElementById("stat-keyboards").textContent = stats.keyboards;
    document.getElementById("stat-mice").textContent      = stats.mice;
    document.getElementById("stat-other").textContent     = stats.other;

    renderCheckoutTable(checkouts.checkouts);
  } catch {
    // Non-critical
  }
}

function renderCheckoutTable(checkouts) {
  const empty = document.getElementById("checkout-empty");
  const table = document.getElementById("checkout-table");
  const tbody = document.getElementById("checkout-tbody");

  tbody.innerHTML = "";

  if (!checkouts || checkouts.length === 0) {
    empty.classList.remove("hidden");
    table.classList.add("hidden");
    return;
  }

  empty.classList.add("hidden");
  table.classList.remove("hidden");

  checkouts.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.full_name)}</td>
      <td>${escapeHtml(row.items.join(", "))}</td>
      <td>${escapeHtml(row.checkout_time)}</td>
      <td>
        <button class="btn-return"
                data-checkout-id="${row.checkout_id}"
                data-student="${escapeHtml(row.full_name)}"
                data-items="${escapeHtml(row.items.join(", "))}">
          Return
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Attach return button listeners
  tbody.querySelectorAll(".btn-return").forEach(btn => {
    btn.addEventListener("click", () => {
      openReturnModal(
        parseInt(btn.dataset.checkoutId, 10),
        btn.dataset.student,
        btn.dataset.items.split(", ")
      );
    });
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function showError(elementId, message) {
  const el = document.getElementById(elementId);
  if (!el) return;
  if (message) {
    el.textContent = message;
    el.classList.remove("hidden");
  } else {
    el.textContent = "";
    el.classList.add("hidden");
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Reports tab ───────────────────────────────────────────────────────────────

function initReportsTab() {
  if (!reportsInitialized) {
    // Set default date range: first day of current month → today
    const today = new Date();
    const yyyy  = today.getFullYear();
    const mm    = String(today.getMonth() + 1).padStart(2, "0");
    const dd    = String(today.getDate()).padStart(2, "0");
    document.getElementById("report-start").value = `${yyyy}-${mm}-01`;
    document.getElementById("report-end").value   = `${yyyy}-${mm}-${dd}`;

    document.getElementById("btn-reports-apply").addEventListener("click", loadReports);
    document.getElementById("btn-export-attendance").addEventListener("click", downloadAttendanceCsv);
    document.getElementById("btn-export-gear").addEventListener("click", downloadGearCsv);

    reportsInitialized = true;
  }
  loadReports();
}

async function loadReports() {
  const start = document.getElementById("report-start").value;
  const end   = document.getElementById("report-end").value;
  if (!start || !end) return;

  const qs = `?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;

  try {
    const [summaryRes, overTimeRes, byMajorRes, byGradeRes, peakDaysRes, gearRes] =
      await Promise.all([
        fetch(`/api/reports/summary${qs}`),
        fetch(`/api/reports/attendance-over-time${qs}`),
        fetch(`/api/reports/by-major${qs}`),
        fetch(`/api/reports/by-grade${qs}`),
        fetch(`/api/reports/peak-days${qs}`),
        fetch(`/api/reports/gear-usage${qs}`),
      ]);

    const [summary, overTime, byMajor, byGrade, peakDays, gear] = await Promise.all([
      summaryRes.json(), overTimeRes.json(), byMajorRes.json(),
      byGradeRes.json(), peakDaysRes.json(), gearRes.json(),
    ]);

    renderSummaryCards(summary);
    renderChart("chart-over-time",  buildBarConfig(overTime,  "Visits",     false));
    renderChart("chart-peak-days",  buildBarConfig(peakDays,  "Visits",     false));
    renderChart("chart-by-major",   buildBarConfig(byMajor,   "Visits",     true));
    renderChart("chart-by-grade",   buildDoughnutConfig(byGrade));
    renderChart("chart-gear-usage", buildBarConfig(gear,      "Checkouts",  false));
  } catch {
    // Non-critical — charts stay blank on error
  }
}

function renderSummaryCards(s) {
  document.getElementById("rpt-total-visits").textContent    = s.total_visits    ?? "—";
  document.getElementById("rpt-unique-students").textContent = s.unique_students ?? "—";
  document.getElementById("rpt-avg-per-day").textContent     =
    s.avg_visits_per_day != null ? Number(s.avg_visits_per_day).toFixed(1) : "—";
  document.getElementById("rpt-gear-total").textContent      = s.total_gear_checkouts ?? "—";
}

function getCsuColors() {
  const style = getComputedStyle(document.documentElement);
  return {
    primary:   style.getPropertyValue("--primary").trim(),
    secondary: style.getPropertyValue("--secondary").trim(),
    border:    style.getPropertyValue("--border").trim(),
    muted:     style.getPropertyValue("--muted-foreground").trim(),
  };
}

function buildBarConfig(data, yLabel, horizontal) {
  const { primary, border, muted } = getCsuColors();
  return {
    type: "bar",
    data: {
      labels: data.labels || [],
      datasets: [{
        label: yLabel,
        data:  data.values || [],
        backgroundColor: primary + "cc",
        borderColor:     primary,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: horizontal ? "y" : "x",
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: border }, ticks: { color: muted } },
        y: { grid: { color: border }, ticks: { color: muted }, beginAtZero: true },
      },
    },
  };
}

function buildDoughnutConfig(data) {
  const { muted } = getCsuColors();
  const palette = [
    "#00543C", "#FFB81C", "#004830", "#e5a518",
    "#006B4E", "#c8921a", "#737373", "#d4d4d4",
  ];
  return {
    type: "doughnut",
    data: {
      labels: data.labels || [],
      datasets: [{
        data:            data.values || [],
        backgroundColor: palette.slice(0, (data.labels || []).length),
        borderColor:     "#ffffff",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: muted, boxWidth: 12, padding: 12 },
        },
      },
    },
  };
}

function renderChart(canvasId, config) {
  if (reportCharts[canvasId]) {
    reportCharts[canvasId].destroy();
  }
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  reportCharts[canvasId] = new Chart(canvas.getContext("2d"), config);
}

function buildReportQs() {
  const start = document.getElementById("report-start").value;
  const end   = document.getElementById("report-end").value;
  return `?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
}

function downloadAttendanceCsv() {
  const a = document.createElement("a");
  a.href = `/api/reports/export/attendance${buildReportQs()}`;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function downloadGearCsv() {
  const a = document.createElement("a");
  a.href = `/api/reports/export/gear${buildReportQs()}`;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
