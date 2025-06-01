// static/js/category-modal.js

document.addEventListener("DOMContentLoaded", function () {
  const openCategoryModalBtn = document.getElementById("openCategoryModalBtn");
  const categoryModal = document.getElementById("categoryModal");
  const closeCategoryModalBtn = document.getElementById("closeCategoryModalBtn");

  if (openCategoryModalBtn && categoryModal && closeCategoryModalBtn) {
    openCategoryModalBtn.onclick = () => {
      categoryModal.style.display = "block";
    };

    closeCategoryModalBtn.onclick = () => {
      categoryModal.style.display = "none";
    };

    window.onclick = function (event) {
      if (event.target === categoryModal) {
        categoryModal.style.display = "none";
      }
    };
  }
});
