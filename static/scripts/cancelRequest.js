// cancel.js
document.addEventListener("DOMContentLoaded", function () {
  // Helper to get CSRF token from cookies
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(name + "=")) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Attach click listeners to all cancel buttons
  document.querySelectorAll(".btn-cancel").forEach((btn) => {
    btn.addEventListener("click", async function (e) {
      e.preventDefault();
      const requestId = this.dataset.requestId;

      if (!confirm("Are you sure you want to cancel this request?")) return;

      // Show loading spinner and disable button
      this.innerHTML =
        '<span class="spinner-border spinner-border-sm"></span> Cancelling...';
      this.disabled = true;

      try {
        const response = await fetch(`/requests/cancel/${requestId}/`, {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: `csrfmiddlewaretoken=${getCookie("csrftoken")}`,
        });

        if (!response.ok) throw new Error("Failed to cancel");

        const data = await response.json();
        if (data.success) {
          this.closest("tr").remove(); // Remove the row on success
        } else {
          throw new Error(data.message || "Cancellation failed");
        }
      } catch (error) {
        alert(error.message);
      } finally {
        // Restore button state
        this.textContent = "Cancel Request";
        this.disabled = false;
      }
    });
  });
});
