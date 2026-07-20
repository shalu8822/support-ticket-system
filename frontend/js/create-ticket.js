Auth.requireLogin();
if (Auth.getRole() === "admin") window.location.href = "admin.html";

renderNavbar("create-ticket");

document.getElementById("ticketForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById("submitBtn");
  const subject = document.getElementById("subject").value.trim();
  const description = document.getElementById("description").value.trim();
  const priority = document.getElementById("priority").value;
  const fileInput = document.getElementById("attachment");

  const formData = new FormData();
  formData.append("subject", subject);
  formData.append("description", description);
  formData.append("priority", priority);
  if (fileInput.files.length > 0) {
    formData.append("attachment", fileInput.files[0]);
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Submitting…";
  try {
    const ticket = await apiFetch("/tickets", { method: "POST", body: formData, isForm: true });
    showToast(`Ticket #${ticket.id} created successfully.`, "success");
    setTimeout(() => (window.location.href = `ticket-details.html?id=${ticket.id}`), 700);
  } catch (err) {
    showToast(err.message, "danger");
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Ticket";
  }
});
