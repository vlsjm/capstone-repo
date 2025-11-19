document.addEventListener('DOMContentLoaded', function () {
    console.log('Charts.js loaded');

    function safeParseJSON(elementId, fallback = []) {
        try {
            const element = document.getElementById(elementId);
            if (!element) {
                console.warn(`Element ${elementId} not found`);
                return fallback;
            }
            const data = JSON.parse(element.textContent);
            console.log(`${elementId} data:`, data);
            return data || fallback;
        } catch (e) {
            console.error(`Error parsing ${elementId}:`, e);
            return fallback;
        }
    }

    // Helper function to check if canvas exists and create chart
    function createChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas ${canvasId} not found`);
            return null;
        }

        try {
            return new Chart(canvas, config);
        } catch (error) {
            console.error(`Error creating chart ${canvasId}:`, error);
            return null;
        }
    }

    // Get data from script tags
    const supplyData = safeParseJSON('supplyData', [0, 0, 0]);
    const propertyData = safeParseJSON('propertyData', [0, 0, 0, 0, 0, 0]);
    const requestStatusData = safeParseJSON('requestStatusData', [0, 0, 0]);
    const damageStatusData = safeParseJSON('damageStatusData', [0, 0, 0]);
    const borrowTrendsData = safeParseJSON('borrowTrendsData', []);
    const propertyCategoriesData = safeParseJSON('propertyCategoriesData', []);
    const userActivityData = safeParseJSON('userActivityData', []);
    const departmentRequestsData = safeParseJSON('departmentRequestsData', []);

    // Chart 1: Supply Status
    createChart('supplyStatusChart', {
        type: 'doughnut',
        data: {
            labels: ['Available', 'Low Stock', 'Out of Stock'],
            datasets: [{
                data: supplyData,
                backgroundColor: ['#4CAF50', '#FFC107', '#F44336'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                }
            }
        }
    });

    // Chart 2: Property Condition
    createChart('propertyConditionChart', {
        type: 'bar',
        data: {
            labels: ['Good', 'Needs Repair', 'Unserviceable', 'Obsolete', 'Not Needed', 'Not Used'],
            datasets: [{
                label: 'Properties',
                data: propertyData,
                backgroundColor: [
                    '#4CAF50',
                    '#FF9800',
                    '#F44336',
                    '#9C27B0',
                    '#607D8B',
                    '#795548'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });

    // Chart 3: Request Status Breakdown
    createChart('requestStatusChart', {
        type: 'pie',
        data: {
            labels: ['Pending', 'Approved', 'Rejected'],
            datasets: [{
                data: requestStatusData,
                backgroundColor: ['#FFC107', '#4CAF50', '#F44336'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                }
            }
        }
    });

    // Chart 4: Damage Report Status
    createChart('damageStatusChart', {
        type: 'doughnut',
        data: {
            labels: ['Pending', 'Reviewed', 'Resolved'],
            datasets: [{
                data: damageStatusData,
                backgroundColor: ['#FF9800', '#2196F3', '#4CAF50'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                }
            }
        }
    });

    // Chart 5: Borrow Request Trends (Fixed to handle empty data)
    if (borrowTrendsData && borrowTrendsData.length > 0) {
        createChart('borrowTrendsChart', {
            type: 'line',
            data: {
                labels: borrowTrendsData.map(item => item.month || ''),
                datasets: [{
                    label: 'Borrow Requests',
                    data: borrowTrendsData.map(item => item.count || 0),
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    } else {
        // Create empty chart with placeholder
        createChart('borrowTrendsChart', {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Borrow Requests',
                    data: [0, 0, 0, 0, 0, 0],
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
    }

    // Chart 6: Top Requested Supplies (with filtering)
    let topRequestedSuppliesChart = null;

    function loadTopRequestedSupplies(days = '', dateFrom = '', dateTo = '', departmentId = '') {
        let url = '/get-top-requested-supplies/?';
        if (departmentId) {
            url += `department=${departmentId}&`;
        }
        if (days) {
            url += `days=${days}&`;
        } else if (dateFrom && dateTo) {
            url += `date_from=${dateFrom}&date_to=${dateTo}&`;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data.length > 0) {
                    const labels = data.data.map(item => item.supply_name);
                    const quantities = data.data.map(item => item.total_quantity);

                    if (topRequestedSuppliesChart) {
                        topRequestedSuppliesChart.destroy();
                    }

                    topRequestedSuppliesChart = createChart('topRequestedSuppliesChart', {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Total Requested Quantity',
                                data: quantities,
                                backgroundColor: '#FF9800',
                                borderColor: '#F57C00',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: {
                                    beginAtZero: true,
                                    ticks: {
                                        stepSize: 1
                                    }
                                }
                            },
                            plugins: {
                                legend: {
                                    display: false
                                }
                            }
                        }
                    });
                } else {
                    // Create empty chart
                    if (topRequestedSuppliesChart) {
                        topRequestedSuppliesChart.destroy();
                    }
                    topRequestedSuppliesChart = createChart('topRequestedSuppliesChart', {
                        type: 'bar',
                        data: {
                            labels: ['No Data'],
                            datasets: [{
                                label: 'Total Requested Quantity',
                                data: [0],
                                backgroundColor: '#E0E0E0'
                            }]
                        },
                        options: {
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: false
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error loading top requested supplies:', error));
    }

    // Load initial data
    loadTopRequestedSupplies();

    // Add event listeners for filtering
    const suppliesDepartmentFilter = document.getElementById('suppliesDepartmentFilter');
    const suppliesDateFilter = document.getElementById('suppliesDateFilter');
    const suppliesDateFrom = document.getElementById('suppliesDateFrom');
    const suppliesDateTo = document.getElementById('suppliesDateTo');
    const suppliesFilterBtn = document.getElementById('suppliesFilterBtn');

    // Department filter change
    if (suppliesDepartmentFilter) {
        suppliesDepartmentFilter.addEventListener('change', function () {
            const departmentId = this.value;
            const days = suppliesDateFilter.value === 'custom' ? '' : suppliesDateFilter.value;
            const dateFrom = suppliesDateFilter.value === 'custom' ? suppliesDateFrom.value : '';
            const dateTo = suppliesDateFilter.value === 'custom' ? suppliesDateTo.value : '';
            loadTopRequestedSupplies(days, dateFrom, dateTo, departmentId);
        });
    }

    if (suppliesDateFilter) {
        suppliesDateFilter.addEventListener('change', function () {
            const departmentId = suppliesDepartmentFilter ? suppliesDepartmentFilter.value : '';
            if (this.value === 'custom') {
                suppliesDateFrom.style.display = 'inline-block';
                suppliesDateTo.style.display = 'inline-block';
                suppliesFilterBtn.style.display = 'inline-block';
            } else {
                suppliesDateFrom.style.display = 'none';
                suppliesDateTo.style.display = 'none';
                suppliesFilterBtn.style.display = 'none';
                loadTopRequestedSupplies(this.value, '', '', departmentId);
            }
        });
    }

    if (suppliesFilterBtn) {
        suppliesFilterBtn.addEventListener('click', function () {
            const departmentId = suppliesDepartmentFilter ? suppliesDepartmentFilter.value : '';
            loadTopRequestedSupplies('', suppliesDateFrom.value, suppliesDateTo.value, departmentId);
        });
    }

    // Chart 7: Department Requests (with filtering)
    let departmentRequestsChartInstance = null;

    function loadDepartmentRequests(days = '', dateFrom = '', dateTo = '') {
        let url = '/get-department-requests-filtered/?';
        if (days) {
            url += `days=${days}&`;
        } else if (dateFrom && dateTo) {
            url += `date_from=${dateFrom}&date_to=${dateTo}&`;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data.length > 0) {
                    const labels = data.data.map(item => item.department);
                    const totals = data.data.map(item => item.total_requests);

                    if (departmentRequestsChartInstance) {
                        departmentRequestsChartInstance.destroy();
                    }

                    departmentRequestsChartInstance = createChart('departmentRequestsChart', {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Total Requests',
                                data: totals,
                                backgroundColor: '#3498db',
                                borderColor: '#2980b9',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        stepSize: 1
                                    }
                                }
                            },
                            plugins: {
                                legend: {
                                    display: false
                                },
                                tooltip: {
                                    callbacks: {
                                        afterBody: function (context) {
                                            const index = context[0].dataIndex;
                                            const depData = data.data[index];
                                            return [
                                                `Supply Requests: ${depData.supply_requests || 0}`,
                                                `Borrow Requests: ${depData.borrow_requests || 0}`,
                                                `Reservations: ${depData.reservations || 0}`
                                            ];
                                        }
                                    }
                                }
                            }
                        }
                    });
                } else {
                    // Create empty chart
                    if (departmentRequestsChartInstance) {
                        departmentRequestsChartInstance.destroy();
                    }
                    departmentRequestsChartInstance = createChart('departmentRequestsChart', {
                        type: 'bar',
                        data: {
                            labels: ['No Data'],
                            datasets: [{
                                label: 'Total Requests',
                                data: [0],
                                backgroundColor: '#E0E0E0'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            },
                            plugins: {
                                legend: {
                                    display: false
                                }
                            }
                        }
                    });
                }
            })
            .catch(error => console.error('Error loading department requests:', error));
    }

    // Load initial data
    loadDepartmentRequests();

    // Add event listeners for department filter
    const departmentDateFilter = document.getElementById('departmentDateFilter');
    const departmentDateFrom = document.getElementById('departmentDateFrom');
    const departmentDateTo = document.getElementById('departmentDateTo');
    const departmentFilterBtn = document.getElementById('departmentFilterBtn');

    if (departmentDateFilter) {
        departmentDateFilter.addEventListener('change', function () {
            if (this.value === 'custom') {
                departmentDateFrom.style.display = 'inline-block';
                departmentDateTo.style.display = 'inline-block';
                departmentFilterBtn.style.display = 'inline-block';
            } else {
                departmentDateFrom.style.display = 'none';
                departmentDateTo.style.display = 'none';
                departmentFilterBtn.style.display = 'none';
                loadDepartmentRequests(this.value);
            }
        });
    }

    if (departmentFilterBtn) {
        departmentFilterBtn.addEventListener('click', function () {
            loadDepartmentRequests('', departmentDateFrom.value, departmentDateTo.value);
        });
    }

    if (userActivityData && userActivityData.length > 0) {
        createChart('userActivityChart', {
            type: 'bar',
            data: {
                labels: userActivityData.map(item => item.role || ''),
                datasets: [{
                    label: 'Activity Count',
                    data: userActivityData.map(item => item.count || 0),
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF'
                    ]
                }]
            },
            options: {
                indexAxis: 'y', // This makes it horizontal (Chart.js 3+ way)
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    } else {
        // Create empty chart
        createChart('userActivityChart', {
            type: 'bar',
            data: {
                labels: ['No Data'],
                datasets: [{
                    label: 'Activity Count',
                    data: [0],
                    backgroundColor: '#E0E0E0'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    console.log('All charts initialization completed');
});

// Additional debugging function
function debugCharts() {
    console.log('=== Chart Debug Info ===');

    // Check if Chart.js is loaded
    console.log('Chart.js loaded:', typeof Chart !== 'undefined');

    // Check all canvas elements
    const canvases = [
        'supplyStatusChart',
        'propertyConditionChart',
        'requestStatusChart',
        'damageStatusChart',
        'borrowTrendsChart',
        'propertyCategoriesChart',
        'departmentRequestsChart',
        'userActivityChart'
    ];

    canvases.forEach(id => {
        const canvas = document.getElementById(id);
        console.log(`${id}:`, canvas ? 'Found' : 'Missing');
    });

    // Check data scripts
    const dataScripts = [
        'supplyData',
        'propertyData',
        'requestStatusData',
        'damageStatusData',
        'borrowTrendsData',
        'propertyCategoriesData',
        'departmentRequestsData',
        'userActivityData'
    ];

    dataScripts.forEach(id => {
        const script = document.getElementById(id);
        console.log(`${id}:`, script ? 'Found' : 'Missing');
        if (script) {
            try {
                const parsed = JSON.parse(script.textContent);
                console.log(`  - Parsed data:`, parsed);
            } catch (e) {
                console.log(`  - Parse error:`, e.message);
            }
        }
    });
}
