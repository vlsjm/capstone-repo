document.addEventListener('DOMContentLoaded', function() {
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

    // Chart 6: Property Categories (Fixed to handle empty data)
    if (propertyCategoriesData && propertyCategoriesData.length > 0) {
        createChart('propertyCategoriesChart', {
            type: 'polarArea',
            data: {
                labels: propertyCategoriesData.map(item => item.category || ''),
                datasets: [{
                    data: propertyCategoriesData.map(item => item.count || 0),
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF',
                        '#FF9F40',
                        '#FF6384',
                        '#C9CBCF'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    } else {
        // Create empty chart
        createChart('propertyCategoriesChart', {
            type: 'polarArea',
            data: {
                labels: ['No Data'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['#E0E0E0']
                }]
            },
            options: {
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
