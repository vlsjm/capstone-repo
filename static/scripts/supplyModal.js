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