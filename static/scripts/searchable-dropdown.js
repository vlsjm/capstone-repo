// Searchable Dropdown Functionality
// This script handles searchable dropdowns for both supply and borrow request forms

function initializeSearchableDropdown(config) {
    const {
        searchInputId,
        dropdownId,
        hiddenInputId,
        categoryFilterId,
        clearSearchBtnId,
        quantityInputId
    } = config;

    const searchInput = document.getElementById(searchInputId);
    const dropdown = document.getElementById(dropdownId);
    const hiddenInput = document.getElementById(hiddenInputId);
    const categoryFilter = document.getElementById(categoryFilterId);
    const clearSearchBtn = document.getElementById(clearSearchBtnId);

    if (!searchInput || !dropdown || !hiddenInput) {
        console.warn(`Searchable dropdown not initialized: missing elements for ${searchInputId}`);
        return;
    }

    const options = dropdown.querySelectorAll('.select-option:not(.no-results):not(.dropdown-header)');

    let isDropdownOpen = false;
    let highlightedIndex = -1;
    let allOptions = Array.from(options);

    // Utility function to highlight matching text
    function highlightMatch(text, searchTerm) {
        if (!searchTerm) return text;
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<span class="highlight-match">$1</span>');
    }

    // Update results count
    function updateResultsCount() {
        const visibleOptions = Array.from(options).filter(opt =>
            opt.style.display !== 'none' && opt.dataset.value !== ''
        );
        const count = visibleOptions.length;
        const resultsCount = dropdown.querySelector('.results-count');
        if (resultsCount) {
            resultsCount.textContent = `${count} item${count !== 1 ? 's' : ''} found`;
        }
    }

    // Toggle dropdown visibility
    function toggleDropdown() {
        isDropdownOpen = !isDropdownOpen;

        if (isDropdownOpen) {
            const inputRect = searchInput.getBoundingClientRect();
            const quantityField = document.getElementById(quantityInputId);
            const quantityRect = quantityField ? quantityField.getBoundingClientRect() : null;

            let dropdownWidth;
            const viewportWidth = window.innerWidth;

            if (viewportWidth <= 768) {
                dropdownWidth = Math.min(inputRect.width, viewportWidth - 32);
                dropdown.style.left = Math.max(16, inputRect.left) + 'px';
                dropdown.style.right = 'auto';
            } else if (viewportWidth <= 1024) {
                const endX = quantityRect ? quantityRect.right : inputRect.right;
                dropdownWidth = endX - inputRect.left;
                dropdown.style.left = inputRect.left + 'px';
                dropdown.style.right = 'auto';
            } else {
                const returnDateField = document.getElementById('return-date-input');
                const returnDateRect = returnDateField ? returnDateField.getBoundingClientRect() : quantityRect;
                const endX = returnDateRect ? returnDateRect.right : inputRect.right;
                dropdownWidth = endX - inputRect.left;
                dropdown.style.left = inputRect.left + 'px';
                dropdown.style.right = 'auto';
            }

            dropdown.style.width = dropdownWidth + 'px';
            dropdown.style.top = (inputRect.bottom + window.scrollY) + 'px';
            dropdown.style.display = 'block';
            dropdown.style.position = 'fixed';
            dropdown.style.zIndex = '999999';

            document.body.appendChild(dropdown);
            searchInput.focus();
        } else {
            dropdown.style.display = 'none';
            if (dropdown.parentNode === document.body) {
                searchInput.closest('.searchable-select-container').appendChild(dropdown);
            }
        }
    }

    // Filter options based on search and category
    function filterOptions() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const selectedCategory = categoryFilter ? categoryFilter.value : '';
        let hasVisibleOptions = false;
        highlightedIndex = -1;

        if (clearSearchBtn) {
            clearSearchBtn.style.display = searchTerm ? 'block' : 'none';
        }

        const currentOptions = dropdown.querySelectorAll('.select-option:not(.dropdown-header):not(.no-results)');

        currentOptions.forEach((option, index) => {
            if (index === 0 && option.dataset.value === '') return;

            const name = (option.dataset.name || '').toLowerCase();
            const description = (option.dataset.description || '').toLowerCase();
            const number = (option.dataset.number || '').toLowerCase();
            const code = (option.dataset.code || '').toLowerCase();
            const categoryId = option.dataset.category;
            const categoryName = (option.dataset.categoryName || '').toLowerCase();

            const matchesSearch = !searchTerm ||
                name.includes(searchTerm) ||
                description.includes(searchTerm) ||
                number.includes(searchTerm) ||
                code.includes(searchTerm) ||
                categoryName.includes(searchTerm);

            const matchesCategory = !selectedCategory || categoryId === selectedCategory;

            const isVisible = matchesSearch && matchesCategory && option.dataset.value !== '';
            option.style.display = isVisible ? 'flex' : 'none';

            if (isVisible && option.dataset.value !== '') {
                hasVisibleOptions = true;

                if (searchTerm) {
                    const optionName = option.querySelector('.option-name');
                    if (optionName) {
                        const originalName = option.dataset.name;
                        optionName.innerHTML = highlightMatch(originalName, searchTerm);
                    }
                } else {
                    const optionName = option.querySelector('.option-name');
                    if (optionName) {
                        optionName.textContent = option.dataset.name;
                    }
                }
            }
        });

        const noResultsOption = dropdown.querySelector('.no-results');
        if (!hasVisibleOptions && (searchTerm || selectedCategory)) {
            if (noResultsOption) {
                noResultsOption.style.display = 'block';
                noResultsOption.textContent = searchTerm
                    ? `No items found for "${searchInput.value}"`
                    : 'No items in this category';
            }
        } else if (noResultsOption) {
            noResultsOption.style.display = 'none';
        }

        updateResultsCount();
    }

    // Select an option
    function selectOption(option) {
        const value = option.dataset.value;
        const text = option.dataset.name || option.textContent;
        const available = option.dataset.available;

        hiddenInput.value = value;
        searchInput.value = text;

        if (available && quantityInputId) {
            const quantityInput = document.getElementById(quantityInputId);
            if (quantityInput) {
                quantityInput.setAttribute('max', available);
                quantityInput.setAttribute('placeholder', `Enter quantity (max ${available})`);
            }
        }

        toggleDropdown();

        const currentOptions = dropdown.querySelectorAll('.select-option:not(.dropdown-header):not(.no-results)');
        currentOptions.forEach(opt => {
            opt.style.display = 'flex';
            const optionName = opt.querySelector('.option-name');
            if (optionName) {
                optionName.textContent = opt.dataset.name;
            }
        });

        if (categoryFilter) {
            categoryFilter.value = '';
        }
        searchInput.value = text;
        if (clearSearchBtn) {
            clearSearchBtn.style.display = 'none';
        }
    }

    // Event listeners
    searchInput.addEventListener('click', function () {
        if (!isDropdownOpen) {
            toggleDropdown();
        }
    });

    searchInput.addEventListener('input', filterOptions);

    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterOptions);
    }

    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function () {
            searchInput.value = '';
            hiddenInput.value = '';
            clearSearchBtn.style.display = 'none';
            filterOptions();
            searchInput.focus();
        });
    }

    dropdown.addEventListener('click', function (e) {
        const option = e.target.closest('.select-option');
        if (option && !option.classList.contains('no-results') && !option.classList.contains('dropdown-header')) {
            selectOption(option);
        }
    });

    document.addEventListener('click', function (e) {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            if (isDropdownOpen) {
                toggleDropdown();
            }
        }
    });

    searchInput.addEventListener('keydown', function (e) {
        const visibleOptions = Array.from(options).filter(opt => opt.style.display !== 'none' && !opt.classList.contains('no-results'));

        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();

            if (!isDropdownOpen) {
                toggleDropdown();
                return;
            }

            options.forEach(opt => opt.classList.remove('highlighted'));

            if (e.key === 'ArrowDown') {
                highlightedIndex = Math.min(highlightedIndex + 1, visibleOptions.length - 1);
            } else {
                highlightedIndex = Math.max(highlightedIndex - 1, 0);
            }

            if (visibleOptions[highlightedIndex]) {
                visibleOptions[highlightedIndex].classList.add('highlighted');
                visibleOptions[highlightedIndex].scrollIntoView({ block: 'nearest' });
            }
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (highlightedIndex >= 0 && visibleOptions[highlightedIndex]) {
                selectOption(visibleOptions[highlightedIndex]);
            }
        } else if (e.key === 'Escape') {
            toggleDropdown();
        }
    });

    window.addEventListener('scroll', function () {
        if (isDropdownOpen && dropdown.parentNode === document.body) {
            toggleDropdown();
        }
    });

    let resizeTimeout;
    window.addEventListener('resize', function () {
        if (isDropdownOpen && dropdown.parentNode === document.body) {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(function () {
                toggleDropdown();
            }, 100);
        }
    });
}

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initializeSearchableDropdown };
}
