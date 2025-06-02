document.addEventListener('DOMContentLoaded', function () {
  const modal = document.getElementById('modifyQuantityModal');
  const closeBtn = document.getElementById('closeModifyQuantityModalBtn');
  const propertySelect = document.getElementById('property_id');
  const openBtn = document.getElementById('openModifyQuantityModalBtn');

  if (openBtn) {
    openBtn.addEventListener('click', function () {
      modal.style.display = 'block';

      // Initialize Select2 after showing the modal
      if (window.jQuery && $.fn.select2) {
        $(propertySelect).select2({
          width: '100%',
          placeholder: 'Select a property',
          allowClear: true,
          dropdownParent: $(modal)
        });
      }
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', function () {
      modal.style.display = 'none';
      resetForm();
    });
  }

  window.addEventListener('click', function (event) {
    if (event.target === modal) {
      modal.style.display = 'none';
      resetForm();
    }
  });

  function resetForm() {
    const form = modal.querySelector('form');
    if (form) {
      form.reset();
      if ($(propertySelect).hasClass('select2-hidden-accessible')) {
        $(propertySelect).val(null).trigger('change');
      }
    }
  }
});
