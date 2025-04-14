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
  
    // Check if canvas elements exist before initializing charts
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
  
    if (document.getElementById("propertyConditionChart")) {
      new Chart(document.getElementById("propertyConditionChart").getContext("2d"), {
        type: "bar",
        data: {
          labels: ["New", "Good", "Needs Repair", "Damaged"],
          datasets: [
            {
              data: propertyData,
              backgroundColor: ["#4caf50", "#2196f3", "#ff9800", "#f44336"],
            },
          ],
        },
      });
    }
  });
  