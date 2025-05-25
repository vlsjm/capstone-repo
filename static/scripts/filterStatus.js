function filterStatus(status) {
  const tables = document.querySelectorAll('.status-table');
  tables.forEach(table => {
    if (status === 'all' || table.dataset.status === status) {
      table.style.display = '';
    } else {
      table.style.display = 'none';
    }
  });
}
