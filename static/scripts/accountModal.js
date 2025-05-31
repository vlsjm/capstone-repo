document.addEventListener('DOMContentLoaded', () => {
  const createAccountModal = document.getElementById('createAccountModal');
  const openModalBtn = document.getElementById('openModalBtn');
  const closeModalBtn = document.getElementById('closeModalBtn');

  openModalBtn.addEventListener('click', () => {
    createAccountModal.style.display = 'block';
  });

  closeModalBtn.addEventListener('click', () => {
    createAccountModal.style.display = 'none';
  });

  window.addEventListener('click', (event) => {
    if (event.target === createAccountModal) {
      createAccountModal.style.display = 'none';
    }
  });
});
