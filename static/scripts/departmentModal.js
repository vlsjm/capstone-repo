document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const addDeptModal = document.getElementById('addDepartmentModal');
  const openDeptModalBtn = document.getElementById('openDepartmentModalBtn'); // NOTE: matches your button ID in HTML
  const closeDeptModalBtn = document.getElementById('closeDepartmentModalBtn');


  // Open Add Department Modal
  openDeptModalBtn.addEventListener('click', () => {
    addDeptModal.style.display = 'block';
  });


  // Close Add Department Modal
  closeDeptModalBtn.addEventListener('click', () => {
    addDeptModal.style.display = 'none';
  });


  // Close Add Department Modal when clicking outside content
  window.addEventListener('click', (event) => {
    if (event.target === addDeptModal) {
      addDeptModal.style.display = 'none';
    }
  });


  // Edit Department Modal Elements
  const editModal = document.getElementById('editDepartmentModal');
  const closeEditModalBtn = document.getElementById('closeEditModal'); // matches your HTML span close ID
  const editForm = document.getElementById('editDepartmentForm');


  // Open Edit Modal on Edit Button Click
  document.querySelectorAll('.btn-edit').forEach((btn) => {
    btn.addEventListener('click', () => {
      const deptId = btn.getAttribute('data-id');
      const deptName = btn.getAttribute('data-name');


      document.getElementById('editDeptId').value = deptId;
      document.getElementById('editDeptName').value = deptName;


      editModal.style.display = 'block';
    });
  });


  // Close Edit Modal
  closeEditModalBtn.addEventListener('click', () => {
    editModal.style.display = 'none';
  });


  // Close Edit Modal when clicking outside content
  window.addEventListener('click', (event) => {
    if (event.target === editModal) {
      editModal.style.display = 'none';
    }
  });


  // Submit Edit Department Form
  editForm.addEventListener('submit', (e) => {
    e.preventDefault();


    const deptId = document.getElementById('editDeptId').value;
    const newName = document.getElementById('editDeptName').value;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;


    fetch(`/edit-department/${deptId}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrfToken,
      },
      body: `name=${encodeURIComponent(newName)}`,
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          // Update the name in the department table row
          // Find the button with this deptId and update data-name attribute & related cell text
          const editBtn = document.querySelector(`.btn-edit[data-id='${deptId}']`);
          if (editBtn) {
            editBtn.setAttribute('data-name', newName);
            // Also update the corresponding table cell text (2nd column in that row)
            const row = editBtn.closest('tr');
            if (row) {
              row.children[1].textContent = newName;
            }
          }
          editModal.style.display = 'none';
        } else {
          alert('Failed to update department.');
        }
      })
      .catch(() => alert('Error updating department.'));
  });


  // Delete Department with Confirmation Modal
  const deleteModal = document.getElementById('deleteDepartmentModal');
  const closeDeleteModalBtn = document.getElementById('closeDeleteModal');
  const deleteDeptNameSpan = document.getElementById('deleteDeptName');
  const deleteForm = document.getElementById('deleteDepartmentForm');
  let deleteDeptId = null;


  // Open Delete Confirmation Modal on Delete Button Click
  document.querySelectorAll('.btn-delete').forEach((btn) => {
    btn.addEventListener('click', () => {
      deleteDeptId = btn.getAttribute('data-id');
      const deptName = btn.getAttribute('data-name');
      deleteDeptNameSpan.textContent = deptName;
      deleteModal.style.display = 'block';
    });
  });


  // Close Delete Modal
  closeDeleteModalBtn.addEventListener('click', () => {
    deleteModal.style.display = 'none';
  });


  // Close Delete Modal when clicking outside content
  window.addEventListener('click', (event) => {
    if (event.target === deleteModal) {
      deleteModal.style.display = 'none';
    }
  });


  // Handle Delete Department Form submission
  deleteForm.addEventListener('submit', (e) => {
    e.preventDefault();


    if (!deleteDeptId) return;


    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;


    fetch(`/delete-department/${deleteDeptId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        console.log('Response:', data); // Debug log
        if (data.success) {
          // Remove the row from the table
          const delBtn = document.querySelector(`.btn-delete[data-id='${deleteDeptId}']`);
          if (delBtn) {
            const row = delBtn.closest('tr');
            if (row) row.remove();
          }
          deleteModal.style.display = 'none';
        } else {
          alert(data.error || "Failed to delete department.");
          deleteModal.style.display = 'none';
        }
      })
      .catch((error) => {
        console.error('Error:', error); // Debug log
        alert("Error deleting department. Please try again.");
        deleteModal.style.display = 'none';
      });
  });
});



