document.addEventListener('DOMContentLoaded', function () {
  const modal = document.getElementById('modifyQuantityModal');
  const closeBtn = document.getElementById('closeModifyQuantityModalBtn');
  const openBtn = document.getElementById('openModifyQuantityModalBtn');
  const barcodeInput = document.getElementById('barcode_input');
  const submitBtn = document.getElementById('modifyQuantitySubmitBtn');
  const form = document.getElementById('modifyQuantityForm');
  let lastScannedBarcode = '';
  let scanTimeout = null;

  if (openBtn) {
    openBtn.addEventListener('click', function () {
      modal.style.display = 'block';
      barcodeInput.focus();
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

  // Handle barcode scanning
  barcodeInput.addEventListener('input', function (e) {
    const barcode = e.target.value;

    // Clear any existing timeout
    if (scanTimeout) {
      clearTimeout(scanTimeout);
    }

    // Set a new timeout to process the barcode
    scanTimeout = setTimeout(() => {
      if (barcode.length > 0) {
        // Make an AJAX call to get property info by barcode
        fetch(`/get_property_by_barcode/${barcode}/`)
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              // Update the form with property information
              document.getElementById('property_id').value = data.property.id;
              document.getElementById('scanned_property_name').textContent = data.property.name;
              document.getElementById('scanned_property_quantity').textContent = data.property.current_quantity;
              document.getElementById('property_info').style.display = 'block';
              submitBtn.disabled = false;

              // If it's the same barcode being scanned multiple times, increment quantity
              if (lastScannedBarcode === barcode) {
                const amountInput = document.getElementById('amount');
                amountInput.value = parseInt(amountInput.value) + 1;
              } else {
                // Reset amount to 1 for new item
                document.getElementById('amount').value = 1;
              }
              lastScannedBarcode = barcode;
            } else {
              // Handle case when barcode is not found
              document.getElementById('property_info').style.display = 'none';
              submitBtn.disabled = true;
              alert('Property not found for this barcode.');
            }
            // Clear the barcode input and maintain focus
            barcodeInput.value = '';
            barcodeInput.focus();
          })
          .catch(error => {
            console.error('Error:', error);
            alert('Error fetching property information.');
            barcodeInput.value = '';
            barcodeInput.focus();
          });
      }
    }, 100); // Small delay to ensure complete barcode is captured
  });

  // Handle form submission
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      if (!document.getElementById('property_id').value) {
        alert('Please scan a valid property barcode first.');
        return;
      }

      const formData = new FormData(this);
      fetch(this.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Update the displayed quantity
            document.getElementById('scanned_property_quantity').textContent = data.new_quantity;

            // Show success message
            alert('Quantity updated successfully!');

            // Reset form and close modal
            modal.style.display = 'none';
            resetForm();

            // Reload page to show updated quantities
            window.location.reload();
          } else {
            alert(data.error || 'Error modifying quantity. Please try again.');
          }
        })
        .catch(error => {
          console.error('Error:', error);
          alert('Error modifying quantity. Please try again.');
        });
    });
  }

  // Handle Enter key from barcode scanner
  barcodeInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault(); // Prevent form submission
      // The input event handler will process the barcode
    }
  });

  function resetForm() {
    if (form) {
      form.reset();
      document.getElementById('property_info').style.display = 'none';
      document.getElementById('scanned_property_name').textContent = '';
      document.getElementById('scanned_property_quantity').textContent = '';
      submitBtn.disabled = true;
      lastScannedBarcode = '';
      barcodeInput.focus();
    }
  }
});
