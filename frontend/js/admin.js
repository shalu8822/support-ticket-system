Auth.requireAdmin();
renderNavbar("admin");

let charts = {};

// ------------------------------------------------------------------ Tabs --
document.querySelectorAll("#adminTabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#adminTabs button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll("main section").forEach((s) => s.classList.add("d-none"));
    document.getElementById(`tab-${btn.dataset.tab}`).classList.remove("d-none");

    if (btn.dataset.tab === "tickets") loadTickets();
    if (btn.dataset.tab === "users") loadUsers();
  });
});

// --------------------------------------------------------------- Overview --
function renderChart(id, type, labels, data, colors) {
  const ctx = document.getElementById(id);
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(ctx, {
    type,
    data: { labels, datasets: [{ label: "Tickets", data, backgroundColor: colors }] },
    options: {
      plugins: { legend: { display: type === "doughnut", position: "bottom" } },
      scales: type === "doughnut" ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

async function loadOverview() {
  const stats = await apiFetch("/admin/analytics");

  document.getElementById("statsRow").innerHTML = `
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value">${stats.total_tickets}</div><div class="text-muted">Total Tickets</div></div></div>
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value text-danger">${stats.status_counts["Open"] || 0}</div><div class="text-muted">Open</div></div></div>
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value text-success">${stats.status_counts["Resolved"] || 0}</div><div class="text-muted">Resolved</div></div></div>
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value">${stats.total_users}</div><div class="text-muted">Users</div></div></div>`;

  renderChart(
    "statusChart", "doughnut",
    Object.keys(stats.status_counts), Object.values(stats.status_counts),
    ["#ef4444", "#f59e0b", "#10b981"]
  );
  renderChart(
    "priorityChart", "bar",
    Object.keys(stats.priority_counts), Object.values(stats.priority_counts),
    ["#6b7280", "#3b82f6", "#dc2626"]
  );
  renderChart(
    "monthlyChart", "line",
    stats.tickets_per_month.map((m) => m.label), stats.tickets_per_month.map((m) => m.count),
    "#4f46e5"
  );
  renderChart(
    "activeUsersChart", "bar",
    stats.most_active_users.map((u) => u.name), stats.most_active_users.map((u) => u.count),
    "#06b6d4"
  );
}

// ---------------------------------------------------------------- Tickets --
async function loadTickets() {
  const params = {
    search: document.getElementById("searchInput").value.trim(),
    status: document.getElementById("statusFilter").value,
    priority: document.getElementById("priorityFilter").value,
  };
  const tbody = document.getElementById("ticketsBody");
  tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">Loading tickets…</td></tr>`;

  try {
    const tickets = await apiFetch("/admin/tickets", { params });
    if (tickets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No tickets match your filters.</td></tr>`;
      return;
    }
    tbody.innerHTML = tickets
      .map(
        (t) => `
      <tr>
        <td>${t.id}</td>
        <td>${escapeHtml(t.subject)}</td>
        <td>${escapeHtml(t.customer_name || "—")}</td>
        <td><span class="${priorityBadgeClass(t.priority)}">${t.priority}</span></td>
        <td><span class="${statusBadgeClass(t.status)}">${t.status}</span></td>
        <td>${formatDate(t.created_at)}</td>
        <td class="d-flex gap-1">
          <a href="ticket-details.html?id=${t.id}" class="btn btn-sm btn-outline-primary">View</a>
          <button class="btn btn-sm btn-outline-danger" data-delete-ticket="${t.id}">Delete</button>
        </td>
      </tr>`
      )
      .join("");

    tbody.querySelectorAll("[data-delete-ticket]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.deleteTicket;
        const ok = await confirmDialog(`Delete ticket #${id}? This cannot be undone.`, "Delete");
        if (!ok) return;
        try {
          await apiFetch(`/admin/tickets/${id}`, { method: "DELETE" });
          showToast(`Ticket #${id} deleted.`, "info");
          loadTickets();
        } catch (err) {
          showToast(err.message, "danger");
        }
      });
    });
  } catch (err) {
    showToast(err.message, "danger");
  }
}

document.getElementById("applyFiltersBtn").addEventListener("click", loadTickets);
document.getElementById("searchInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadTickets();
});

// ------------------------------------------------------------------ Users --
async function loadUsers() {
  const tbody = document.getElementById("usersBody");
  tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">Loading users…</td></tr>`;

  try {
    const users = await apiFetch("/admin/users");
    if (users.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No registered customers yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = users
      .map(
        (u) => `
      <tr>
        <td>${u.id}</td>
        <td>${escapeHtml(u.name)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${formatDate(u.created_at)}</td>
        <td class="d-flex gap-1">
          <button class="btn btn-sm btn-outline-secondary" data-reset="${u.id}">Reset Password</button>
          <button class="btn btn-sm btn-outline-danger" data-delete-user="${u.id}" data-name="${escapeHtml(u.name)}">Delete</button>
        </td>
      </tr>`
      )
      .join("");

    tbody.querySelectorAll("[data-reset]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const result = await apiFetch(`/admin/users/${btn.dataset.reset}/reset-password`, { method: "PUT" });
          showInfoModal(
            "Temporary Password Generated",
            `<p>Share this temporary password with the user securely:</p>
             <code class="fs-5 d-block p-2 bg-light rounded">${result.temporary_password}</code>`
          );
        } catch (err) {
          showToast(err.message, "danger");
        }
      });
    });

    tbody.querySelectorAll("[data-delete-user]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const ok = await confirmDialog(
          `Delete ${btn.dataset.name} and all their tickets? This cannot be undone.`, "Delete"
        );
        if (!ok) return;
        try {
          await apiFetch(`/admin/users/${btn.dataset.deleteUser}`, { method: "DELETE" });
          showToast(`${btn.dataset.name} deleted.`, "info");
          loadUsers();
        } catch (err) {
          showToast(err.message, "danger");
        }
      });
    });
  } catch (err) {
    showToast(err.message, "danger");
  }
}

(async () => {
  try {
    await loadOverview();
  } catch (err) {
    showToast(err.message, "danger");
  }
})();
