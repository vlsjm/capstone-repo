// modals.js
document.addEventListener("DOMContentLoaded", function () {
  // Modal elements
  const borrowModal = document.getElementById("borrowModal");
  const pendingModal = document.getElementById("pendingModal");

  // Initialize modals as hidden
  borrowModal.style.display = "none";
  pendingModal.style.display = "none";

  // Borrow Modal Controls
  document.getElementById("openBorrowModalBtn").addEventListener("click", function () {
    borrowModal.style.display = "block";
    pendingModal.style.display = "none";
  });

  document.getElementById("closeBorrowModalBtn").addEventListener("click", function () {
    borrowModal.style.display = "none";
  });

  // Pending Modal Controls
  document.getElementById("showPendingBtn").addEventListener("click", function () {
    pendingModal.style.display = "block";
    borrowModal.style.display = "none";
  });

  document.querySelector("#pendingModal .close").addEventListener("click", function () {
    pendingModal.style.display = "none";
  });

  // Close modals when clicking outside
  window.addEventListener("click", function (event) {
    if (event.target === borrowModal) borrowModal.style.display = "none";
    if (event.target === pendingModal) pendingModal.style.display = "none";
  });

  // Update UI when no requests left
  function updatePendingRequestsUI() {
    const tbody = document.querySelector(".pending-table tbody");
    if (!tbody || tbody.children.length === 0) {
      const tableContainer = document.querySelector(".table-container");
      if (tableContainer) {
        tableContainer.innerHTML = `
          <div class="no-requests" style="text-align: center; padding: 20px;">
            <p>You have no pending requests</p>
          </div>
        `;
      }
    }
  }

  // Show error message function (optional)
  function showError(message) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "error-message";
    errorDiv.style.color = "#f44336";
    errorDiv.style.padding = "10px";
    errorDiv.style.margin = "10px 0";
    errorDiv.style.border = "1px solid #f44336";
    errorDiv.style.borderRadius = "4px";
    errorDiv.textContent = message;

    const modalContent = document.querySelector(".modal-content");
    modalContent.prepend(errorDiv);

    setTimeout(() => {
      errorDiv.style.transition = "opacity 0.5s ease";
      errorDiv.style.opacity = "0";
      setTimeout(() => errorDiv.remove(), 500);
    }, 3000);
  }
});
