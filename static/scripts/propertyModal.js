document.addEventListener('DOMContentLoaded', function() {
  const addModal = document.getElementById("addPropertyModal");
  const openBtn = document.getElementById("openModalBtn");
  const closeBtn = document.getElementById("closeModalBtn");
  const editModal = document.getElementById("editPropertyModal");
  const closeEditModalBtn = document.getElementById("closeEditModalBtn");

  if (openBtn) openBtn.onclick = () => addModal.style.display = "block";
  if (closeBtn) closeBtn.onclick = () => addModal.style.display = "none";

  // Close the Edit Property Modal
  if (closeEditModalBtn && editModal) {
    closeEditModalBtn.addEventListener("click", () => {
      editModal.style.display = "none";
    });
  }

  // Close modals when clicking outside
  window.onclick = (event) => {
    if (event.target == addModal) {
      addModal.style.display = "none";
    }
    if (event.target == editModal) {
      editModal.style.display = "none";
    }
  };

  // Add click handlers to all edit buttons
  document.querySelectorAll('.edit-btn').forEach(button => {
    button.addEventListener('click', function() {
      // Get all data attributes
      const data = this.dataset;
      
      // Set values in the edit form
      document.getElementById('edit_id').value = data.id;
      document.getElementById('edit_property_number').value = data.propertyNumber;
      document.getElementById('edit_property_name').value = data.name;
      document.getElementById('edit_description').value = data.description;
      document.getElementById('edit_unit_of_measure').value = data.unit;
      document.getElementById('edit_unit_value').value = data.value;
      document.getElementById('edit_overall_quantity').value = data.overallQuantity;
      document.getElementById('edit_location').value = data.location;
      document.getElementById('edit_condition').value = data.condition;
      document.getElementById('edit_category').value = data.category;
      document.getElementById('edit_availability').value = data.availability;

      // Show the modal
      editModal.style.display = 'block';
    });
  });
});

