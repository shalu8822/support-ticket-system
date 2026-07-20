Auth.requireLogin();
renderNavbar(Auth.getRole() === "admin" ? "admin" : "dashboard");

const params = new URLSearchParams(window.location.search);
const ticketId = params.get("id");
const isAdmin = Auth.getRole() === "admin";

if (!ticketId) {
  window.location.href = isAdmin ? "admin.html" : "dashboard.html";
}

let currentTicket = null;
let currentUserId = null;

function renderHeader(ticket) {
  document.getElementById("ticketHeader").innerHTML = `
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
      <h4 class="mb-0">Ticket #${ticket.id} — ${escapeHtml(ticket.subject)}</h4>
      <div class="d-flex gap-2">
        <span class="${priorityBadgeClass(ticket.priority)} fs-6">${ticket.priority}</span>
        <span class="${statusBadgeClass(ticket.status)} fs-6">${ticket.status}</span>
      </div>
    </div>
    <p class="text-muted mb-0 mt-1">Submitted by ${escapeHtml(ticket.customer_name || "—")}${ticket.agent_name ? ` · Assigned to ${escapeHtml(ticket.agent_name)}` : ""}</p>`;
}

function renderBody(ticket) {
  const attachmentHtml = ticket.attachment_filename
    ? `<p><strong>Attachment:</strong>
         <a href="${API_BASE}/uploads/${ticket.attachment_filename}" target="_blank">
           <i class="bi bi-paperclip"></i> ${escapeHtml(ticket.original_filename)}
         </a></p>`
    : "";

  document.getElementById("ticketBody").innerHTML = `
    <p class="mb-1"><strong>Description</strong></p>
    <p class="text-muted" id="descriptionText">${escapeHtml(ticket.description)}</p>
    ${attachmentHtml}
    <hr>
    <p class="small text-muted mb-0">Created: ${formatDateTime(ticket.created_at)}</p>
    <p class="small text-muted">Last updated: ${formatDateTime(ticket.updated_at)}</p>
    ${isAdmin ? renderAdminControls(ticket) : ""}`;

  if (isAdmin) wireAdminControls(ticket);
}

function renderAdminControls(ticket) {
  return `
    <div class="border rounded p-3 mt-3">
      <h6 class="mb-3">Agent Controls</h6>
      <div class="row g-2">
        <div class="col-sm-6">
          <label class="form-label small">Status</label>
          <select class="form-select form-select-sm" id="adminStatus">
            ${["Open", "In Progress", "Resolved"].map((s) => `<option value="${s}" ${ticket.status === s ? "selected" : ""}>${s}</option>`).join("")}
          </select>
        </div>
        <div class="col-sm-6">
          <label class="form-label small">Priority</label>
          <select class="form-select form-select-sm" id="adminPriority">
            ${["Low", "Medium", "High"].map((p) => `<option value="${p}" ${ticket.priority === p ? "selected" : ""}>${p}</option>`).join("")}
          </select>
        </div>
      </div>
      <button class="btn btn-sm btn-primary mt-3" id="saveAdminBtn">Save Changes</button>
    </div>`;
}

function wireAdminControls(ticket) {
  document.getElementById("saveAdminBtn").addEventListener("click", async () => {
    const status = document.getElementById("adminStatus").value;
    const priority = document.getElementById("adminPriority").value;
    try {
      const updated = await apiFetch(`/admin/tickets/${ticket.id}`, {
        method: "PUT",
        body: { status, priority },
      });
      showToast("Ticket updated. The customer has been notified.", "success");
      currentTicket = updated;
      renderHeader(updated);
      renderBody(updated);
      renderActions(updated);
    } catch (err) {
      showToast(err.message, "danger");
    }
  });
}

function renderActions(ticket) {
  const actions = document.getElementById("ticketActions");
  const isOwner = ticket.user_id === currentUserId;
  const canEdit = isOwner && ticket.status === "Open" && !isAdmin;

  let html = `<a href="${isAdmin ? "admin.html" : "dashboard.html"}" class="btn btn-outline-secondary"><i class="bi bi-arrow-left"></i> Back</a>`;

  if (canEdit) {
    html += `<button class="btn btn-outline-primary" id="editBtn"><i class="bi bi-pencil"></i> Edit</button>`;
  }
  if (isOwner && !isAdmin) {
    html += `<button class="btn btn-outline-danger" id="deleteBtn"><i class="bi bi-trash"></i> Delete</button>`;
  }
  if (isAdmin) {
    html += `<button class="btn btn-outline-danger" id="deleteBtn"><i class="bi bi-trash"></i> Delete Ticket</button>`;
  }

  actions.innerHTML = html;

  if (canEdit) {
    document.getElementById("editBtn").addEventListener("click", () => showEditForm(ticket));
  }
  document.getElementById("deleteBtn")?.addEventListener("click", async () => {
    const ok = await confirmDialog(
      `Delete ticket #${ticket.id}? This cannot be undone.`, "Delete"
    );
    if (!ok) return;
    try {
      const endpoint = isAdmin ? `/admin/tickets/${ticket.id}` : `/tickets/${ticket.id}`;
      await apiFetch(endpoint, { method: "DELETE" });
      showToast("Ticket deleted.", "info");
      setTimeout(() => (window.location.href = isAdmin ? "admin.html" : "dashboard.html"), 600);
    } catch (err) {
      showToast(err.message, "danger");
    }
  });
}

function showEditForm(ticket) {
  document.getElementById("ticketBody").innerHTML = `
    <div class="mb-2">
      <label class="form-label small">Subject</label>
      <input type="text" class="form-control" id="editSubject" value="${escapeHtml(ticket.subject)}">
    </div>
    <div class="mb-2">
      <label class="form-label small">Description</label>
      <textarea class="form-control" id="editDescription" rows="4">${escapeHtml(ticket.description)}</textarea>
    </div>
    <div class="d-flex gap-2">
      <button class="btn btn-primary btn-sm" id="saveEditBtn">Save</button>
      <button class="btn btn-outline-secondary btn-sm" id="cancelEditBtn">Cancel</button>
    </div>`;

  document.getElementById("cancelEditBtn").addEventListener("click", () => renderBody(currentTicket));
  document.getElementById("saveEditBtn").addEventListener("click", async () => {
    const subject = document.getElementById("editSubject").value.trim();
    const description = document.getElementById("editDescription").value.trim();
    try {
      const updated = await apiFetch(`/tickets/${ticket.id}`, {
        method: "PUT",
        body: { subject, description },
      });
      currentTicket = updated;
      showToast("Ticket updated.", "success");
      renderHeader(updated);
      renderBody(updated);
    } catch (err) {
      showToast(err.message, "danger");
    }
  });
}

function renderComments(comments) {
  const list = document.getElementById("commentsList");
  if (comments.length === 0) {
    list.innerHTML = `<p class="text-muted mb-0">No replies yet.</p>`;
    return;
  }
  list.innerHTML = comments
    .map((c) => {
      const bubbleClass = c.is_internal ? "internal" : "public";
      const authorLabel = c.author_role === "admin" ? `${escapeHtml(c.author_name)} (Support Agent)` : escapeHtml(c.author_name);
      return `
      <div class="comment-bubble ${bubbleClass}">
        <div class="d-flex justify-content-between">
          <strong class="small">${authorLabel}${c.is_internal ? ' <span class="badge bg-warning text-dark ms-1">Internal</span>' : ""}</strong>
          <span class="text-muted small">${formatDateTime(c.created_at)}</span>
        </div>
        <div>${escapeHtml(c.comment)}</div>
      </div>`;
    })
    .join("");
}

async function loadTicket() {
  currentTicket = await apiFetch(`/tickets/${ticketId}`);
  renderHeader(currentTicket);
  renderBody(currentTicket);
  renderActions(currentTicket);
}

async function loadComments() {
  const comments = await apiFetch(`/tickets/${ticketId}/comments`);
  renderComments(comments);
}

if (isAdmin) {
  document.getElementById("internalCheckWrap").classList.remove("d-none");
}

document.getElementById("commentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const commentText = document.getElementById("commentText").value.trim();
  const isInternal = isAdmin && document.getElementById("internalCheck").checked;
  if (!commentText) return;

  try {
    await apiFetch(`/tickets/${ticketId}/comments`, {
      method: "POST",
      body: { comment: commentText, is_internal: isInternal },
    });
    document.getElementById("commentText").value = "";
    document.getElementById("internalCheck").checked = false;
    await loadComments();
    showToast("Reply posted.", "success");
  } catch (err) {
    showToast(err.message, "danger");
  }
});

(async () => {
  try {
    const profile = await apiFetch("/profile");
    currentUserId = profile.id;
    await loadTicket();
    await loadComments();
  } catch (err) {
    showToast(err.message, "danger");
  }
})();
