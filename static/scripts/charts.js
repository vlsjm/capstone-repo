document.addEventListener("DOMContentLoaded", function () {
  // Get JSON data from template
  let supplyData = JSON.parse(document.getElementById("supplyData").textContent);
  let propertyData = JSON.parse(document.getElementById("propertyData").textContent);

  // Debug: Check if data is loaded correctly
  console.log("Supply Data:", supplyData);
  console.log("Property Data:", propertyData);

  // Ensure data is an array of numbers
  supplyData = supplyData.map(Number);
  propertyData = propertyData.map(Number);

  // Supply Status Pie Chart
  if (document.getElementById("supplyStatusChart")) {
    new Chart(document.getElementById("supplyStatusChart").getContext("2d"), {
      type: "pie",
      data: {
        labels: ["Available", "Low Stock", "Out of Stock"],
        datasets: [
          {
            data: supplyData,
            backgroundColor: ["#4caf50", "#ff9800", "#f44336"],
          },
        ],
      },
    });
  }

  // Property Condition Bar Chart — UPDATED to 6 conditions
  if (document.getElementById("propertyConditionChart")) {
    new Chart(document.getElementById("propertyConditionChart").getContext("2d"), {
      type: "bar",
      data: {
        labels: [
          "In good condition",
          "Needing repair",
          "Unserviceable",
          "Obsolete",
          "No longer needed",
          "Not used since purchased",
        ],
        datasets: [
          {
            data: propertyData,
            backgroundColor: [
              "#4caf50", // green
              "#ff9800", // orange
              "#f44336", // red
              "#9e9e9e", // gray
              "#607d8b", // blue gray
              "#795548", // brown
            ],
          },
        ],
      },
      options: {
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0, // show integers only
            },
          },
        },
      },
    });
  }
});