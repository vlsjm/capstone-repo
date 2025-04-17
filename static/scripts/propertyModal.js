// Open Add Property Modal
const modal = document.getElementById("addPropertyModal");
const openBtn = document.getElementById("openModalBtn");
const closeBtn = document.getElementById("closeModalBtn");

openBtn.onclick = () => modal.style.display = "block";
closeBtn.onclick = () => modal.style.display = "none";

// Close modal when clicking outside
window.onclick = (event) => {
  if (event.target == modal) {
    modal.style.display = "none";
  }
};

// Open Edit Modal and populate it with data
function openEditModal(propertyId) {
  const modal = document.getElementById('editPropertyModal');
  const row = document.querySelector(`tr[data-id='${propertyId}']`);
  
  // Populate form fields with the corresponding data attributes
  document.getElementById('editId').value = propertyId;
  document.getElementById('editPropertyName').value = row.dataset.name;
  document.getElementById('editQuantity').value = row.dataset.quantity;
  document.getElementById('editBarcode').value = row.dataset.barcode;
  document.getElementById('editCondition').value = row.dataset.condition;
  document.getElementById('editAvailability').value = row.dataset.availability;
  document.getElementById('editAssignedTo').value = row.dataset.assigned;
  document.getElementById('editAvailableForRequest').checked = row.dataset.request === "True";

  // Ensure date format is correct (YYYY-MM-DD)
  const dateAcquired = row.dataset.date;
  const formattedDate = dateAcquired ? dateAcquired.split('T')[0] : '';  // Extract the date portion if the date is in a datetime format
  document.getElementById('editDateAcquired').value = formattedDate;
  
  // Update form action dynamically
  document.getElementById('editPropertyForm').action = `/edit-property/${propertyId}/`;
  
  // Show the modal
  modal.style.display = 'block';
}

// Close Edit Modal
document.getElementById('closeEditModal').onclick = function () {
  document.getElementById('editPropertyModal').style.display = 'none';
};

// Open Delete Modal and set the form action
function openDeleteModal(propertyId) {
  const modal = document.getElementById('deletePropertyModal');
  const form = document.getElementById('deletePropertyForm');

  // Set form action to delete the property
  form.action = `/delete-property/${propertyId}/`;
  modal.style.display = 'block';
}

// Close Delete Modal
document.getElementById('closeDeleteModal').onclick = function () {
  document.getElementById('deletePropertyModal').style.display = 'none';
};
