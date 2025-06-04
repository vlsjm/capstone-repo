document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const roleFilter = document.getElementById('roleFilter');
    const departmentFilter = document.getElementById('departmentFilter');
    const table = document.querySelector('.searchable-table');


    function filterTable() {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedRole = roleFilter.value.toLowerCase();
        const selectedDepartment = departmentFilter.value.toLowerCase();


        const rows = table.getElementsByTagName('tr');


        // Start from index 1 to skip the header row
        for (let i = 1; i < rows.length; i++) {
            const row = rows[i];
            const cells = row.getElementsByTagName('td');
            if (cells.length === 0) continue;


            const username = cells[1].textContent.toLowerCase();
            const firstName = cells[2].textContent.toLowerCase();
            const lastName = cells[3].textContent.toLowerCase();
            const email = cells[4].textContent.toLowerCase();
            const role = cells[5].textContent.toLowerCase();
            const department = cells[6].textContent.toLowerCase();


            // Check if the row matches all filters
            const matchesSearch = username.includes(searchTerm) ||
                firstName.includes(searchTerm) ||
                lastName.includes(searchTerm) ||
                email.includes(searchTerm) ||
                role.includes(searchTerm) ||
                department.includes(searchTerm);


            const matchesRole = !selectedRole || role.includes(selectedRole);
            const matchesDepartment = !selectedDepartment || department.includes(selectedDepartment);


            // Show/hide row based on all filters
            row.style.display = (matchesSearch && matchesRole && matchesDepartment) ? '' : 'none';
        }
    }


    // Add event listeners for all filter inputs
    searchInput.addEventListener('input', filterTable);
    roleFilter.addEventListener('change', filterTable);
    departmentFilter.addEventListener('change', filterTable);
});
