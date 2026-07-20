/** Small shared UI helpers: toasts, confirm dialogs, badge classes. */

function ensureToastContainer() {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container position-fixed bottom-0 end-0 p-3";
    document.body.appendChild(container);
  }
  return container;
}

/** @param {'success'|'danger'|'warning'|'info'} type */
function showToast(message, type = "info") {
  const container = ensureToastContainer();
  const id = `toast-${Date.now()}`;
  const el = document.createElement("div");
  el.id = id;
  el.className = `toast align-items-center text-bg-${type} border-0`;
  el.setAttribute("role", "alert");
  el.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(el);
  const toast = new bootstrap.Toast(el, { delay: 4000 });
  toast.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

/** Returns a Promise<boolean> resolved true/false depending on the button clicked. */
function confirmDialog(message, confirmLabel = "Confirm") {
  return new Promise((resolve) => {
    let modalEl = document.getElementById("confirmModal");
    if (modalEl) modalEl.remove();

    modalEl = document.createElement("div");
    modalEl.id = "confirmModal";
    modalEl.className = "modal fade";
    modalEl.tabIndex = -1;
    modalEl.innerHTML = `
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-body p-4">
            <p class="mb-0">${message}</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" data-action="cancel">Cancel</button>
            <button type="button" class="btn btn-danger" data-action="confirm">${confirmLabel}</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(modalEl);

    const modal = new bootstrap.Modal(modalEl);
    modalEl.querySelector('[data-action="confirm"]').addEventListener("click", () => {
      modal.hide();
      resolve(true);
    });
    modalEl.querySelector('[data-action="cancel"]').addEventListener("click", () => resolve(false));
    modalEl.addEventListener("hidden.bs.modal", () => modalEl.remove());
    modal.show();
  });
}

function showInfoModal(title, bodyHtml) {
  let modalEl = document.getElementById("infoModal");
  if (modalEl) modalEl.remove();

  modalEl = document.createElement("div");
  modalEl.id = "infoModal";
  modalEl.className = "modal fade";
  modalEl.tabIndex = -1;
  modalEl.innerHTML = `
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">${title}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">${bodyHtml}</div>
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" data-bs-dismiss="modal">Close</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(modalEl);
  const modal = new bootstrap.Modal(modalEl);
  modalEl.addEventListener("hidden.bs.modal", () => modalEl.remove());
  modal.show();
}

function statusBadgeClass(status) {
  return `badge badge-status-${status.replace(/\s+/g, "")}`;
}

function priorityBadgeClass(priority) {
  return `badge badge-priority-${priority.replace(/\s+/g, "")}`;
}

function formatDate(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

function formatDateTime(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleString(undefined, {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
