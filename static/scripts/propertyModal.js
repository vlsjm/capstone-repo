// Add Property Modal functionality
const addModal = document.getElementById("addPropertyModal");
const openBtn = document.getElementById("openModalBtn");
const closeBtn = document.getElementById("closeModalBtn");

openBtn.onclick = () => addModal.style.display = "block";
closeBtn.onclick = () => addModal.style.display = "none";

// Edit Property Modal functionality
const editModal = document.getElementById("editPropertyModal");
const closeEditBtn = document.getElementById("closeEditModal");

closeEditBtn.onclick = () => editModal.style.display = "none";

// Delete Property Modal functionality
const deleteModal = document.getElementById("deletePropertyModal");
const closeDeleteBtn = document.getElementById("closeDeleteModal");

closeDeleteBtn.onclick = () => deleteModal.style.display = "none";

// Close any modal when clicking outside of it
window.onclick = (event) => {
  if (event.target == addModal) {
    addModal.style.display = "none";
  } else if (event.target == editModal) {
    editModal.style.display = "none";
  } else if (event.target == deleteModal) {
    deleteModal.style.display = "none";
  }
};

function openEditModal(id) {
  const row = document.querySelector(`tr[data-id='${id}']`);
  
  // Convert the date format to YYYY-MM-DD if necessary
  const dateAcquired = new Date(row.dataset.date);
  const formattedDate = dateAcquired.toISOString().split('T')[0];
  
  // Set form action for the edit
  const editForm = document.getElementById('editPropertyForm');
  editForm.action = `/edit-property/${id}/`;
  
  // Populate form fields
  document.getElementById('editId').value = id;
  document.getElementById('editPropertyName').value = row.dataset.name;
  document.getElementById('editQuantity').value = row.dataset.quantity;
  document.getElementById('editDateAcquired').value = formattedDate;
  document.getElementById('editBarcode').value = row.dataset.barcode;
  
  // Make sure these match the actual values in your database
  // The dropdown/select field for condition should be populated
  const conditionField = document.getElementById('editCondition');
  if (conditionField.tagName === 'SELECT') {
    // If it's a select dropdown, find the option with matching text
    Array.from(conditionField.options).forEach(option => {
      if (option.text === row.dataset.condition) {
        option.selected = true;
      }
    });
  } else {
    // If it's a text input, just set the value
    conditionField.value = row.dataset.condition;
  }
  
  // Same for availability
  const availabilityField = document.getElementById('editAvailability');
  if (availabilityField.tagName === 'SELECT') {
    Array.from(availabilityField.options).forEach(option => {
      if (option.text === row.dataset.availability) {
        option.selected = true;
      }
    });
  } else {
    availabilityField.value = row.dataset.availability;
  }
  
  document.getElementById('editAssignedTo').value = row.dataset.assigned !== "Unassigned" ? row.dataset.assigned : "";
  
  // Set the select dropdown value correctly
  const availableForRequestSelect = document.getElementById('editAvailableForRequest');
  availableForRequestSelect.value = row.dataset.request === "True" ? "True" : "False";

  // Show the modal
  document.getElementById('editPropertyModal').style.display = "block";
}

// Open Delete Modal and set the form action
function openDeleteModal(propertyId) {
  // Set form action to delete the property
  document.getElementById('deletePropertyForm').action = `/delete-property/${propertyId}/`;
  deleteModal.style.display = 'block';
}