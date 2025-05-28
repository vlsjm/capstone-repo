const addModal = document.getElementById("addPropertyModal");
const openBtn = document.getElementById("openModalBtn");
const closeBtn = document.getElementById("closeModalBtn");

openBtn.onclick = () => addModal.style.display = "block";
closeBtn.onclick = () => addModal.style.display = "none";

// Close the Edit Property Modal
const closeEditModalBtn = document.getElementById("closeEditModalBtn");
const editModal = document.getElementById("editPropertyModal");

if (closeEditModalBtn && editModal) {
  closeEditModalBtn.addEventListener("click", () => {
    editModal.style.display = "none";
  });
}

// ✅ Combine both modal close-on-outside-click into one
window.onclick = (event) => {
  if (event.target == addModal) {
    addModal.style.display = "none";
  }
  if (event.target == editModal) {
    editModal.style.display = "none";
  }
};


document.querySelectorAll('.edit-btn').forEach(button => {
  button.addEventListener('click', function () {
    document.getElementById('edit_id').value = this.dataset.id;
    document.getElementById('edit_property_name').value = this.dataset.name;
    document.getElementById('edit_description').value = this.dataset.description;
    document.getElementById('edit_barcode').value = this.dataset.barcode;
    document.getElementById('edit_unit_of_measure').value = this.dataset.unit;
    document.getElementById('edit_unit_value').value = this.dataset.value;
    document.getElementById('edit_quantity').value = this.dataset.quantity;
    document.getElementById('edit_location').value = this.dataset.location;

    // Set selected options for condition and category
    document.getElementById('edit_condition').value = this.dataset.condition;
    document.getElementById('edit_category').value = this.dataset.category;

    document.getElementById('editPropertyModal').style.display = 'block';
  });
});