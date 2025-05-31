document.addEventListener('DOMContentLoaded', () => {
  // Add Department Modal
  const addDeptModal = document.getElementById('addDepartmentModal');
  const openDeptModalBtn = document.getElementById('openDeptModalBtn');
  const closeDeptModalBtn = document.getElementById('closeDeptModalBtn');

  openDeptModalBtn.addEventListener('click', () => {
    addDeptModal.style.display = 'block';
  });

  closeDeptModalBtn.addEventListener('click', () => {
    addDeptModal.style.display = 'none';
  });

  window.addEventListener('click', (event) => {
    if (event.target === addDeptModal) {
      addDeptModal.style.display = 'none';
    }
  });

  // DELETE Department
  document.querySelectorAll('.del-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      if (confirm('Are you sure you want to delete this department?')) {
        fetch(`/delete-department/${id}/`)
          .then((res) => res.json())
          .then((data) => {
            if (data.success) {
              document.getElementById(`dept-row-${id}`).remove();
            }
          });
      }
    });
  });

  // Edit Department Modal
  const editModal = document.getElementById('editDepartmentModal');
  const closeEditModalBtn = document.getElementById('closeEditDeptModalBtn');
  const editForm = document.getElementById('editDepartmentForm');

  // Open Edit Modal
  document.querySelectorAll('.edit-btn').forEach((btn) => {
    btn.addEventListener('click', function () {
      const deptId = this.dataset.id;
      const deptName = document.querySelector(`.dept-name[data-id='${deptId}']`).innerText;

      document.getElementById('editDeptId').value = deptId;
      document.getElementById('editDeptName').value = deptName;
      editModal.style.display = 'block';
    });
  });

  // Close Edit Modal
  closeEditModalBtn.addEventListener('click', () => {
    editModal.style.display = 'none';
  });

  window.addEventListener('click', (e) => {
    if (e.target === editModal) {
      editModal.style.display = 'none';
    }
  });

  // Submit Edit Form
  editForm.addEventListener('submit', function (e) {
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
          document.querySelector(`.dept-name[data-id='${deptId}']`).innerText = newName;
          editModal.style.display = 'none';
        } else {
          alert('Failed to update department.');
        }
      });
  });

  // Helper to get CSRF token (optional if you don't use it elsewhere)
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + '=') {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
});


