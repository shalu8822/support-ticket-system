Auth.requireLogin();
if (Auth.getRole() === "admin") window.location.href = "admin.html";

renderNavbar("dashboard");

let allTickets = [];

async function loadProfile() {
  const profile = await apiFetch("/profile");
  document.getElementById("userName").textContent = profile.name;
  document.getElementById("userEmail").textContent = profile.email;
}

function renderStats(tickets) {
  const total = tickets.length;
  const open = tickets.filter((t) => t.status === "Open").length;
  const inProgress = tickets.filter((t) => t.status === "In Progress").length;
  const resolved = tickets.filter((t) => t.status === "Resolved").length;

  document.getElementById("statsRow").innerHTML = `
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value">${total}</div><div class="text-muted">Total Tickets</div></div></div>
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value text-danger">${open}</div><div class="text-muted">Open</div></div></div>
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value text-warning">${inProgress}</div><div class="text-muted">In Progress</div></div></div>
    <div class="col-6 col-md-3"><div class="card stat-card p-3 text-center"><div class="stat-value text-success">${resolved}</div><div class="text-muted">Resolved</div></div></div>`;
}

function renderTable() {
  const search = document.getElementById("searchInput").value.trim().toLowerCase();
  const statusFilter = document.getElementById("statusFilter").value;

  const filtered = allTickets.filter((t) => {
    const matchesSearch = !search || t.subject.toLowerCase().includes(search);
    const matchesStatus = !statusFilter || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const tbody = document.getElementById("ticketsBody");
  const emptyState = document.getElementById("emptyState");

  if (allTickets.length === 0) {
    tbody.innerHTML = "";
    emptyState.classList.remove("d-none");
    return;
  }
  emptyState.classList.add("d-none");

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No tickets match your filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered
    .map(
      (t) => `
    <tr>
      <td>${t.id}</td>
      <td>${escapeHtml(t.subject)}</td>
      <td><span class="${priorityBadgeClass(t.priority)}">${t.priority}</span></td>
      <td><span class="${statusBadgeClass(t.status)}">${t.status}</span></td>
      <td>${formatDate(t.created_at)}</td>
      <td><a href="ticket-details.html?id=${t.id}" class="btn btn-sm btn-outline-primary">View</a></td>
    </tr>`
    )
    .join("");
}

async function loadTickets() {
  allTickets = await apiFetch("/tickets");
  renderStats(allTickets);
  renderTable();
}

document.getElementById("searchInput").addEventListener("input", renderTable);
document.getElementById("statusFilter").addEventListener("change", renderTable);

(async () => {
  try {
    await Promise.all([loadProfile(), loadTickets()]);
  } catch (err) {
    showToast(err.message, "danger");
  }
})();
