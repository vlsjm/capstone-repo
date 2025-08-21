document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const roleFilter = document.getElementById('roleFilter');
    const departmentFilter = document.getElementById('departmentFilter');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const table = document.querySelector('.searchable-table');

    // Function to get current URL parameters
    function getUrlParameters() {
        const params = new URLSearchParams(window.location.search);
        return {
            page: params.get('page') || '1',
            search: params.get('search') || '',
            role: params.get('role') || '',
            department: params.get('department') || ''
        };
    }

    // Function to update URL with filters
    function updateUrl(search, role, department) {
        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (role) params.append('role', role);
        if (department) params.append('department', department);
        params.append('page', '1'); // Reset to first page when applying filters
        
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }

    // Initialize filters from URL parameters
    function initializeFilters() {
        const params = getUrlParameters();
        searchInput.value = params.search || '';
        roleFilter.value = params.role || '';
        departmentFilter.value = params.department || '';
    }

    // Apply filters when the button is clicked
    function applyFilters() {
        const searchTerm = searchInput.value;
        const selectedRole = roleFilter.value;
        const selectedDepartment = departmentFilter.value;

        updateUrl(searchTerm, selectedRole, selectedDepartment);
    }

    // Add event listener for the apply filters button
    applyFiltersBtn.addEventListener('click', applyFilters);

    // Handle enter key in search input
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });

    // Initialize filters from URL on page load
    initializeFilters();

    // Update pagination links to preserve filters
    function updatePaginationLinks() {
        const paginationLinks = document.querySelectorAll('.actlog-pagination a');
        const currentParams = new URLSearchParams(window.location.search);
        
        paginationLinks.forEach(link => {
            const linkUrl = new URL(link.href);
            const pageParam = linkUrl.searchParams.get('page');
            
            // Copy all current parameters except page
            const newParams = new URLSearchParams();
            for (const [key, value] of currentParams.entries()) {
                if (key !== 'page') {
                    newParams.append(key, value);
                }
            }
            // Add the page parameter
            if (pageParam) {
                newParams.append('page', pageParam);
            }
            
            link.href = `${window.location.pathname}?${newParams.toString()}`;
        });
    }

    // Update pagination links on page load
    updatePaginationLinks();
});
