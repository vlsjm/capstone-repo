// Test log to check if file is loaded
console.log('accountModal.js loaded');


document.addEventListener('DOMContentLoaded', function () {
  console.log('DOM Content Loaded in accountModal.js');


  // Get elements
  const generateBtn = document.getElementById('generatePasswordBtn');
  const toggleBtn = document.getElementById('togglePasswordBtn');
  const passwordInput = document.getElementById('id_password');


  console.log('Elements found:', {
    generateBtn: !!generateBtn,
    toggleBtn: !!toggleBtn,
    passwordInput: !!passwordInput
  });


  // Password toggle functionality
  if (toggleBtn && passwordInput) {
    console.log('Adding click handler to toggle button');
    toggleBtn.addEventListener('click', function () {
      console.log('Toggle button clicked');
      if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
      } else {
        passwordInput.type = 'password';
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
      }
    });
  }


  // Password generation functionality
  if (generateBtn && passwordInput) {
    console.log('Adding click handler to generate button');
    generateBtn.addEventListener('click', function () {
      console.log('Generate button clicked');
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
      let password = '';


      // Ensure at least one of each type
      password += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random() * 26)]; // Uppercase
      password += 'abcdefghijklmnopqrstuvwxyz'[Math.floor(Math.random() * 26)]; // Lowercase
      password += '0123456789'[Math.floor(Math.random() * 10)]; // Number
      password += '!@#$%^&*'[Math.floor(Math.random() * 8)]; // Special


      // Fill the rest
      for (let i = password.length; i < 12; i++) {
        password += chars[Math.floor(Math.random() * chars.length)];
      }


      // Shuffle the password
      password = password.split('').sort(() => 0.5 - Math.random()).join('');


      passwordInput.value = password;
      try {
        navigator.clipboard.writeText(password);
        alert('Password generated and copied to clipboard!');
      } catch (err) {
        alert('Password generated!');
      }
    });
  } else {
    console.error('Generate button or password input not found when setting up click handler');
  }


  // Modal functionality
  const modal = document.getElementById('createAccountModal');
  const openBtn = document.getElementById('openModalBtn');
  const closeBtn = document.getElementById('closeModalBtn');


  if (openBtn) {
    console.log('Adding click handler to open button');
    openBtn.addEventListener('click', function () {
      console.log('Open button clicked');
      modal.style.display = 'block';
    });
  } else {
    console.error('Open button not found when setting up click handler');
  }


  if (closeBtn) {
    console.log('Adding click handler to close button');
    closeBtn.addEventListener('click', function () {
      console.log('Close button clicked');
      modal.style.display = 'none';
    });
  } else {
    console.error('Close button not found when setting up click handler');
  }


  window.addEventListener('click', function (event) {
    if (event.target === modal) {
      console.log('Modal clicked outside');
      modal.style.display = 'none';
    }
  });
});


