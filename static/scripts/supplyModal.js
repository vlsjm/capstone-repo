const modal = document.getElementById("addSupplyModal");
const openBtn = document.getElementById("openModalBtn");
const closeBtn = document.getElementById("closeModalBtn");

openBtn.onclick = () => modal.style.display = "block";
closeBtn.onclick = () => modal.style.display = "none";
window.onclick = (event) => {
  if (event.target == modal) {
    modal.style.display = "none";
  }
};

// Edit Supply Modal
const editModal = document.getElementById("editSupplyModal");
const closeEditBtn = document.getElementById("closeEditModalBtn");

document.querySelectorAll(".edit-btn").forEach(button => {
  button.addEventListener("click", () => {
    document.getElementById("edit_id").value = button.dataset.id;
    document.getElementById("edit_name").value = button.dataset.name;
    document.getElementById("edit_current_quantity").value = button.dataset.currentQuantity;
    document.getElementById("edit_minimum_threshold").value = button.dataset.minimumThreshold;
    document.getElementById("edit_category").value = button.dataset.category;
    document.getElementById("edit_subcategory").value = button.dataset.subcategory;
    document.getElementById("edit_description").value = button.dataset.description || '';
    document.getElementById("edit_date").value = button.dataset.date;
    document.getElementById("edit_expiration_date").value = button.dataset.expirationDate || '';
    document.getElementById("edit_barcode").value = button.dataset.barcode;
    editModal.style.display = "block";
  });
});

closeEditBtn.onclick = () => editModal.style.display = "none";
window.addEventListener("click", event => {
  if (event.target === editModal) {
    editModal.style.display = "none";
  }
});

document.addEventListener('DOMContentLoaded', function() {
  // Auto-hide success messages after 2 seconds
  const successMessage = document.querySelector('.success-container');
  if (successMessage) {
    setTimeout(function() {
      successMessage.style.opacity = '0';
      successMessage.style.transition = 'opacity 0.3s ease-out';
      setTimeout(function() {
        successMessage.remove();
      }, 300);
    }, 2000);
  }

  // History Modal functionality
  const historyModal = document.getElementById('historyModal');
  const historyBtns = document.querySelectorAll('.history-btn');
  const closeHistoryModalBtn = document.getElementById('closeHistoryModalBtn');

  if (!historyModal || !historyBtns.length || !closeHistoryModalBtn) {
    console.error('Missing required elements:', {
      historyModal: !!historyModal,
      historyBtns: historyBtns.length,
      closeHistoryModalBtn: !!closeHistoryModalBtn
    });
    return;
  }

  historyBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const supplyId = this.dataset.id;
      historyModal.style.display = 'block';
      
      const historyTableBody = document.getElementById('historyTableBody');
      historyTableBody.innerHTML = '<tr><td colspan="6">Loading...</td></tr>';
      
      // Fetch history data
      fetch(`/get_supply_history/${supplyId}/`)
        .then(response => response.json())
        .then(data => {
          // Populate history table
          historyTableBody.innerHTML = '';
          if (data.history.length === 0) {
            historyTableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">No changes have been made to this supply yet.</td></tr>';
          } else {
            data.history.forEach(entry => {
              const row = document.createElement('tr');
              row.innerHTML = `
                <td>${entry.date}</td>
                <td>${entry.action}</td>
                <td>${entry.field_name}</td>
                <td>${entry.old_value}</td>
                <td>${entry.new_value}</td>
                <td>${entry.user}</td>
              `;
              historyTableBody.appendChild(row);
            });
          }
        })
        .catch(error => {
          console.error('Error fetching history:', error);
          historyTableBody.innerHTML = '<tr><td colspan="6">Error loading history data</td></tr>';
        });
    });
  });

  closeHistoryModalBtn.addEventListener('click', function() {
    historyModal.style.display = 'none';
  });

  window.addEventListener('click', function(event) {
    if (event.target == historyModal) {
      historyModal.style.display = 'none';
    }
  });
});