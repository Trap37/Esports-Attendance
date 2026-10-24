"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let activeReturnCheckoutId = null;
let activeEditScannerCode = null;

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupScanInput();
  setupRegisterModal();
  setupCheckoutModal();
  setupReturnModal();
  setupHistoryTab();
  setupStudentsTab();
  setupReportsTab();
  setupEditModal();
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
  return [...document.querySelectorAll(".modal-overlay")].some(
    (m) => !m.classList.contains("hidden"),
  );
}

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
  if (!anyModalOpen()) focusScanInput();
}

function closeAllModals() {
  document
    .querySelectorAll(".modal-overlay")
    .forEach((m) => m.classList.add("hidden"));
  focusScanInput();
}

// Close modals on Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAllModals();
});

// Close on overlay background click
function setupOverlayDismiss() {
  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });
}

// Wire up [data-close] buttons
function setupModalCloseButtons() {
  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(btn.dataset.close));
  });
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab-btn")
        .forEach((b) => b.classList.remove("active"));
      document
        .querySelectorAll(".tab-panel")
        .forEach((p) => p.classList.add("hidden"));
      btn.classList.add("active");
      const panel = document.getElementById(`tab-${btn.dataset.tab}`);
      if (panel) panel.classList.remove("hidden");
      if (btn.dataset.tab === "gear") {
        loadGearTab();
      } else if (btn.dataset.tab === "students") {
        loadStudents();
      } else if (btn.dataset.tab === "history") {
        loadHistory();
      } else if (btn.dataset.tab === "attendance") {
        focusScanInput();
      }
    });
  });
}

// ── Attendance scan ───────────────────────────────────────────────────────────
function setupScanInput() {
  const input = document.getElementById("scan-input");
  input.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter") return;
    const code = input.value.trim();
    if (!code) return;
    input.value = "";

    try {
      const res = await fetch("/api/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scan_id: code }),
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

  document
    .getElementById("btn-register-submit")
    .addEventListener("click", submitRegister);

  // Allow Enter on any field to submit
  ["reg-name", "reg-csu-id", "reg-scan-id", "reg-major", "reg-grade"].forEach(
    (id) => {
      document.getElementById(id).addEventListener("keydown", (e) => {
        if (e.key === "Enter") submitRegister();
      });
    },
  );
}

function clearRegisterForm() {
  ["reg-name", "reg-csu-id", "reg-scan-id", "reg-major"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  document.getElementById("reg-grade").value = "";
  showError("reg-error", null);
}

async function submitRegister() {
  const body = {
    full_name: document.getElementById("reg-name").value.trim(),
    csu_id: document.getElementById("reg-csu-id").value.trim(),
    scan_id: document.getElementById("reg-scan-id").value.trim(),
    major: document.getElementById("reg-major").value.trim(),
    grade_level: document.getElementById("reg-grade").value,
  };

  if (!body.full_name) {
    showError("reg-error", "Full name is required.");
    document.getElementById("reg-name").focus();
    return;
  }
  if (!body.school_id) {
    showError("reg-error", "CSU ID is required.");
    document.getElementById("reg-csu-id").focus();
    return;
  }
  if (!body.scan_id) {
    showError("reg-error", "Scan ID is required.");
    document.getElementById("reg-scan-id").focus();
    return;
  }
  if (!body.major) {
    showError("reg-error", "Major is required.");
    document.getElementById("reg-major").focus();
    return;
  }

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
  scanInput.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter") return;
    await submitCheckout();
  });

  document
    .getElementById("btn-checkout-submit")
    .addEventListener("click", submitCheckout);
}

function clearCheckoutForm() {
  ["chk-keyboard", "chk-mouse", "chk-mousepad", "chk-headset"].forEach((id) => {
    document.getElementById(id).checked = false;
  });
  document.getElementById("checkout-scan-input").value = "";
  showError("checkout-error", null);
}

async function submitCheckout() {
  const keyboard = document.getElementById("chk-keyboard").checked;
  const mouse = document.getElementById("chk-mouse").checked;
  const mousepad = document.getElementById("chk-mousepad").checked;
  const headset = document.getElementById("chk-headset").checked;
  const code = document.getElementById("checkout-scan-input").value.trim();

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
      body: JSON.stringify({
        scan_id: code,
        keyboard,
        mouse,
        mousepad,
        headset,
      }),
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
  scanInput.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter") return;
    await submitReturn();
  });

  document
    .getElementById("btn-return-submit")
    .addEventListener("click", submitReturn);
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
      body: JSON.stringify({ scan_id: code }),
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
    const stats = await statsRes.json();
    const checkouts = await checkoutsRes.json();

    document.getElementById("stat-total").textContent = stats.total;
    document.getElementById("stat-keyboards").textContent = stats.keyboards;
    document.getElementById("stat-mice").textContent = stats.mice;
    document.getElementById("stat-other").textContent = stats.other;

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

  checkouts.forEach((row) => {
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
  tbody.querySelectorAll(".btn-return").forEach((btn) => {
    btn.addEventListener("click", () => {
      openReturnModal(
        parseInt(btn.dataset.checkoutId, 10),
        btn.dataset.student,
        btn.dataset.items.split(", "),
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

// ── History tab ───────────────────────────────────────────────────────────────
function setupHistoryTab() {
  const today = new Date().toISOString().slice(0, 10);
  const start = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);
  document.getElementById("hist-start").value = start;
  document.getElementById("hist-end").value = today;
  document
    .getElementById("btn-history-load")
    .addEventListener("click", loadHistory);
}

async function loadHistory() {
  const start = document.getElementById("hist-start").value;
  const end = document.getElementById("hist-end").value;
  const summary = document.getElementById("history-summary");
  const empty = document.getElementById("history-empty");
  const table = document.getElementById("history-table");
  const tbody = document.getElementById("history-tbody");

  if (!start || !end) {
    summary.textContent = "Please pick both a start and end date.";
    empty.classList.remove("hidden");
    table.classList.add("hidden");
    return;
  }

  try {
    const res = await fetch(
      `/api/attendance/history?start=${start}&end=${end}`,
    );
    const data = await res.json();
    if (!res.ok) {
      summary.textContent = data.error || "Failed to load history.";
      empty.classList.remove("hidden");
      table.classList.add("hidden");
      return;
    }
    summary.textContent = `${data.count} scan(s) between ${data.start} and ${data.end}.`;
    tbody.innerHTML = "";
    if (data.rows.length === 0) {
      empty.classList.remove("hidden");
      table.classList.add("hidden");
      return;
    }
    empty.classList.add("hidden");
    table.classList.remove("hidden");
    data.rows.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(r.check_in_time)}</td>
        <td>${escapeHtml(r.day_of_week || "")}</td>
        <td>${escapeHtml(r.full_name || "(unregistered)")}</td>
        <td>${escapeHtml(r.scan_id)}</td>
        <td>${escapeHtml(r.major || "")}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch {
    summary.textContent = "Error communicating with server.";
  }
}

// ── Students tab ──────────────────────────────────────────────────────────────
function setupStudentsTab() {
  const search = document.getElementById("students-search");
  let timer;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(loadStudents, 200);
  });
}

async function loadStudents() {
  const q = document.getElementById("students-search").value.trim();
  const empty = document.getElementById("students-empty");
  const table = document.getElementById("students-table");
  const tbody = document.getElementById("students-tbody");

  try {
    const url = q
      ? `/api/students?q=${encodeURIComponent(q)}`
      : "/api/students";
    const res = await fetch(url);
    const data = await res.json();
    tbody.innerHTML = "";
    if (!data.students || data.students.length === 0) {
      empty.textContent = q
        ? "No students match that search."
        : "No students yet.";
      empty.classList.remove("hidden");
      table.classList.add("hidden");
      return;
    }
    empty.classList.add("hidden");
    table.classList.remove("hidden");
    data.students.forEach((s) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(s.full_name)}</td>
        <td>${escapeHtml(s.csu_id || "")}</td>
        <td>${escapeHtml(s.scan_id)}</td>
        <td>${escapeHtml(s.major || "")}</td>
        <td>${escapeHtml(s.grade_level || "")}</td>
        <td><button class="btn-edit" data-scan="${escapeHtml(s.scan_id)}">Edit</button></td>
      `;
      tbody.appendChild(tr);
    });
    tbody.querySelectorAll(".btn-edit").forEach((btn) => {
      btn.addEventListener("click", () => openEditModal(btn.dataset.scan));
    });
  } catch {
    empty.textContent = "Error loading students.";
    empty.classList.remove("hidden");
    table.classList.add("hidden");
  }
}

// ── Edit Student modal ───────────────────────────────────────────────────────
function setupEditModal() {
  document
    .getElementById("btn-edit-submit")
    .addEventListener("click", submitEdit);
  ["edit-name", "edit-csu-id", "edit-major", "edit-grade"].forEach((id) => {
    document.getElementById(id).addEventListener("keydown", (e) => {
      if (e.key === "Enter") submitEdit();
    });
  });
}

async function openEditModal(scannerCode) {
  showError("edit-error", null);
  try {
    const res = await fetch(`/api/students/${encodeURIComponent(scannerCode)}`);
    if (!res.ok) {
      alert("Could not load student.");
      return;
    }
    const s = await res.json();
    activeEditScannerCode = s.scan_id;
    document.getElementById("edit-scan-id").value = s.scan_id;
    document.getElementById("edit-name").value = s.full_name || "";
    document.getElementById("edit-csu-id").value = s.csu_id || "";
    document.getElementById("edit-major").value = s.major || "";
    document.getElementById("edit-grade").value = s.grade_level || "";
    openModal("modal-edit");
    document.getElementById("edit-name").focus();
  } catch {
    alert("Error loading student.");
  }
}

async function submitEdit() {
  if (!activeEditScannerCode) return;
  const body = {
    full_name: document.getElementById("edit-name").value.trim(),
    csu_id: document.getElementById("edit-csu-id").value.trim(),
    major: document.getElementById("edit-major").value.trim(),
    grade_level: document.getElementById("edit-grade").value,
  };
  if (!body.full_name) {
    showError("edit-error", "Full name is required.");
    return;
  }
  if (!body.csu_id) {
    showError("edit-error", "CSU ID is required.");
    return;
  }
  if (!body.major) {
    showError("edit-error", "Major is required.");
    return;
  }

  try {
    const res = await fetch(
      `/api/students/${encodeURIComponent(activeEditScannerCode)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
    if (res.ok) {
      activeEditScannerCode = null;
      closeModal("modal-edit");
      loadStudents();
    } else {
      const err = await res.json();
      showError("edit-error", err.error || "Update failed.");
    }
  } catch {
    showError("edit-error", "Error communicating with server.");
  }
}

// ── Reports tab ───────────────────────────────────────────────────────────────
function setupReportsTab() {
  const today = new Date().toISOString().slice(0, 10);
  const start = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);
  document.getElementById("rep-start").value = start;
  document.getElementById("rep-end").value = today;
  document.getElementById("btn-export").addEventListener("click", () => {
    const s = document.getElementById("rep-start").value;
    const e = document.getElementById("rep-end").value;
    const t = document.getElementById("rep-type").value;
    const err = document.getElementById("reports-error");
    if (!s || !e) {
      err.textContent = "Please pick both a start and end date.";
      err.classList.remove("hidden");
      return;
    }
    if (s > e) {
      err.textContent = "Start date must be on or before end date.";
      err.classList.remove("hidden");
      return;
    }
    err.classList.add("hidden");
    window.location.href = `/reports/export?start=${s}&end=${e}&type=${t}`;
  });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
