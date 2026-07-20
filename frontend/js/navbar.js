/** Renders the shared navbar into <div id="navbar"></div> based on login state/role. */
function renderNavbar(activePage) {
  const mount = document.getElementById("navbar");
  if (!mount) return;

  const loggedIn = Auth.isLoggedIn();
  const role = Auth.getRole();

  const link = (href, icon, label, page) =>
    `<li class="nav-item"><a class="nav-link ${activePage === page ? "active" : ""}" href="${href}">
       <i class="bi ${icon}"></i> ${label}</a></li>`;

  let links = "";
  if (loggedIn && role === "admin") {
    links += link("admin.html", "bi-speedometer2", "Admin Dashboard", "admin");
  } else if (loggedIn) {
    links += link("dashboard.html", "bi-speedometer2", "Dashboard", "dashboard");
    links += link("create-ticket.html", "bi-plus-circle", "New Ticket", "create-ticket");
  }

  let rightSide = "";
  if (loggedIn) {
    rightSide = `
      <li class="nav-item dropdown me-2">
        <a class="nav-link position-relative" href="#" role="button" data-bs-toggle="dropdown" id="notifBell">
          <i class="bi bi-bell fs-5"></i>
          <span class="notif-dot d-none" id="notifDot"></span>
        </a>
        <ul class="dropdown-menu dropdown-menu-end p-2" style="min-width: 320px;" id="notifList">
          <li class="text-muted small px-2">No notifications yet.</li>
        </ul>
      </li>
      <li class="nav-item"><a class="nav-link" href="logout.html"><i class="bi bi-box-arrow-right"></i> Logout</a></li>`;
  } else {
    rightSide = `
      <li class="nav-item"><a class="nav-link" href="login.html">Login</a></li>
      <li class="nav-item"><a class="btn btn-sm btn-outline-light ms-lg-2" href="register.html">Register</a></li>`;
  }

  mount.innerHTML = `
    <nav class="navbar navbar-expand-lg navbar-dark app-navbar">
      <div class="container">
        <a class="navbar-brand fw-bold" href="index.html"><i class="bi bi-life-preserver"></i> Support Ticket System</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navMain">
          <ul class="navbar-nav ms-auto align-items-lg-center">
            ${links}
            ${rightSide}
          </ul>
        </div>
      </div>
    </nav>`;

  if (loggedIn) loadNotificationsIntoNavbar();
}

async function loadNotificationsIntoNavbar() {
  try {
    const notifications = await apiFetch("/notifications");
    const list = document.getElementById("notifList");
    const dot = document.getElementById("notifDot");
    if (!list) return;

    const unread = notifications.filter((n) => !n.is_read);
    dot.classList.toggle("d-none", unread.length === 0);

    if (notifications.length === 0) {
      list.innerHTML = `<li class="text-muted small px-2">No notifications yet.</li>`;
      return;
    }

    list.innerHTML = notifications
      .slice(0, 8)
      .map(
        (n) => `
      <li>
        <button class="dropdown-item small ${n.is_read ? "" : "fw-semibold"}" data-id="${n.id}">
          ${escapeHtml(n.message)}
          <div class="text-muted" style="font-size: 0.7rem;">${formatDateTime(n.created_at)}</div>
        </button>
      </li>`
      )
      .join("");

    list.querySelectorAll("button[data-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await apiFetch(`/notifications/${btn.dataset.id}/read`, { method: "PUT" });
        loadNotificationsIntoNavbar();
      });
    });
  } catch (err) {
    // Fail silently in the navbar -- notifications are non-critical.
    console.warn("Could not load notifications:", err.message);
  }
}
