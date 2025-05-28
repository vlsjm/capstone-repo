 const modal = document.getElementById("createAccountModal");
    const openBtn = document.getElementById("openModalBtn");
    const closeBtn = document.getElementById("closeModalBtn");

    openBtn.onclick = function() {
      modal.style.display = "block";
    }

    closeBtn.onclick = function() {
      modal.style.display = "none";
    }

    window.onclick = function(event) {
      if (event.target == modal) {
        modal.style.display = "none";
      }
    }

    function filterRole(role) {
      const rows = document.querySelectorAll('.user-row');
      rows.forEach(row => {
        if (role === 'all' || row.dataset.role === role) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });

      // Highlight active button
      document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
      });
      event.target.classList.add('active');
    }