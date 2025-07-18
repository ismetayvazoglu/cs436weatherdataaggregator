// API endpoints
const API_ENDPOINTS = {
    current: '/current',
    history: '/history',
    average: '/average-temperature'
};

// Chart instance
let tempChart;

// DOM elements
const elements = {
    currentWeather: document.getElementById('current-weather-content'),
    averageTemp: document.getElementById('average-temp-content'),
    history: document.getElementById('history-content'),
    refreshButtons: {
        current: document.getElementById('refresh-current'),
        average: document.getElementById('refresh-average'),
        history: document.getElementById('refresh-history'),
        chart: document.getElementById('refresh-chart')
    }
};

// Initialize the dashboard
function initDashboard() {
    // Set up event listeners for refresh buttons
    elements.refreshButtons.current.addEventListener('click', () => fetchCurrentWeather());
    elements.refreshButtons.average.addEventListener('click', () => fetchAverageTemperature());
    elements.refreshButtons.history.addEventListener('click', () => fetchWeatherHistory());
    elements.refreshButtons.chart.addEventListener('click', () => {
        fetchHistoryForChart();
        fetchTemperatureTrend();  // Also refresh the trend image
    });

    // Load initial data
    fetchCurrentWeather();
    fetchAverageTemperature();
    fetchWeatherHistory();
    fetchHistoryForChart();
    fetchTemperatureTrend();
}

// Fetch current weather data
async function fetchCurrentWeather() {
    elements.currentWeather.innerHTML = '<div class="loader"></div>';

    try {
        const response = await fetch(API_ENDPOINTS.current);

        if (!response.ok) {
            throw new Error('Failed to fetch current weather data');
        }

        const data = await response.json();
        displayCurrentWeather(data);
    } catch (error) {
        console.error('Error fetching current weather:', error);
        elements.currentWeather.innerHTML = `<p>Error loading current weather data. ${error.message}</p>`;
    }
}

// Display current weather data
function displayCurrentWeather(data) {
    if (!data || data.error) {
        elements.currentWeather.innerHTML = '<p>No current weather data available.</p>';
        return;
    }

    // Safely access timestamp or use current time as fallback
    let timestamp;
    try {
        timestamp = new Date((data.timestamp?._seconds || Date.now() / 1000) * 1000);
    } catch (e) {
        console.error('Error parsing timestamp:', e);
        timestamp = new Date();
    }
    
    const formattedDate = formatDate(timestamp);

    elements.currentWeather.innerHTML = `
        <div class="weather-now">
            <div class="temp-big">${data.temperature !== undefined ? data.temperature : 'N/A'}°C</div>
            <div class="timestamp">Last updated: ${formattedDate}</div>
        </div>
        <div class="weather-details">
            <div class="detail-item">
                <span class="detail-label">Humidity</span>
                <span class="detail-value">${data.humidity !== undefined ? data.humidity : 'N/A'}%</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Wind Speed</span>
                <span class="detail-value">${data.wind_speed !== undefined ? data.wind_speed : 'N/A'} m/s</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Pressure</span>
                <span class="detail-value">${data.pressure !== undefined ? data.pressure : 'N/A'} hPa</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Conditions</span>
                <span class="detail-value">${data.conditions || 'N/A'}</span>
            </div>
        </div>
    `;
}

// Fetch average temperature
async function fetchAverageTemperature() {
    elements.averageTemp.innerHTML = '<div class="loader"></div>';

    try {
        const response = await fetch(API_ENDPOINTS.average);

        if (!response.ok) {
            throw new Error('Failed to fetch average temperature data');
        }

        const data = await response.json();
        displayAverageTemperature(data);
    } catch (error) {
        console.error('Error fetching average temperature:', error);
        elements.averageTemp.innerHTML = `<p>Error loading average temperature data. ${error.message}</p>`;
    }
}

// Display average temperature
function displayAverageTemperature(data) {
    if (!data || data.error || data.average_temperature === undefined) {
        elements.averageTemp.innerHTML = '<p>No average temperature data available.</p>';
        return;
    }

    elements.averageTemp.innerHTML = `
        <div class="weather-now">
            <div class="temp-big">${data.average_temperature}°C</div>
            <div>24-Hour Average</div>
        </div>
    `;
}

// Fetch weather history
async function fetchWeatherHistory() {
    elements.history.innerHTML = '<div class="loader"></div>';

    try {
        const response = await fetch(API_ENDPOINTS.history);

        if (!response.ok) {
            throw new Error('Failed to fetch weather history data');
        }

        const data = await response.json();
        displayWeatherHistory(data);
    } catch (error) {
        console.error('Error fetching weather history:', error);
        elements.history.innerHTML = `<p>Error loading weather history data. ${error.message}</p>`;
    }
}

// Display weather history
function displayWeatherHistory(data) {
    if (!data || data.length === 0) {
        elements.history.innerHTML = '<p>No weather history data available.</p>';
        return;
    }

    let tableHTML = `
        <table class="history-table">
            <thead>
                <tr>
                    <th>Date & Time</th>
                    <th>Temperature (°C)</th>
                    <th>Humidity (%)</th>
                    <th>Wind Speed (m/s)</th>
                    <th>Conditions</th>
                </tr>
            </thead>
            <tbody>
    `;

    data.forEach(item => {
        // Safely access timestamp or use current time as fallback
        let timestamp;
        try {
            timestamp = new Date((item.timestamp?._seconds || Date.now() / 1000) * 1000);
        } catch (e) {
            timestamp = new Date();
        }
        
        const formattedDate = formatDate(timestamp);

        tableHTML += `
            <tr>
                <td>${formattedDate}</td>
                <td>${item.temperature !== undefined ? item.temperature : 'N/A'}</td>
                <td>${item.humidity !== undefined ? item.humidity : 'N/A'}</td>
                <td>${item.wind_speed !== undefined ? item.wind_speed : 'N/A'}</td>
                <td>${item.conditions || 'N/A'}</td>
            </tr>
        `;
    });

    tableHTML += `
            </tbody>
        </table>
    `;

    elements.history.innerHTML = tableHTML;
}

// Fetch history data for chart
async function fetchHistoryForChart() {
    try {
        const response = await fetch(API_ENDPOINTS.history);

        if (!response.ok) {
            throw new Error('Failed to fetch weather history data for chart');
        }

        const data = await response.json();
        createTempChart(data);
    } catch (error) {
        console.error('Error fetching data for chart:', error);
    }
}

// Create temperature history chart
function createTempChart(data) {
    if (!data || data.length === 0) {
        return;
    }

    // Filter out entries with invalid timestamps or temperatures
    const validData = data.filter(item => 
        item.timestamp && 
        item.timestamp._seconds && 
        item.temperature !== undefined
    );

    if (validData.length === 0) {
        return;
    }

    // Sort data by timestamp (oldest to newest)
    validData.sort((a, b) => {
        const aSeconds = a.timestamp?._seconds || 0;
        const bSeconds = b.timestamp?._seconds || 0;
        return aSeconds - bSeconds;
    });

    // Extract last 20 entries for better visibility
    const limitedData = validData.slice(-20);

    // Extract labels and temperature values
    const labels = limitedData.map(item => {
        const date = new Date((item.timestamp?._seconds || Date.now() / 1000) * 1000);
        return formatTime(date);
    });

    const temperatures = limitedData.map(item => item.temperature);

    // Destroy existing chart if it exists
    if (tempChart) {
        tempChart.destroy();
    }

    // Create new chart
    const ctx = document.getElementById('tempChart').getContext('2d');
    tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Temperature (°C)',
                data: temperatures,
                borderColor: 'rgb(30, 136, 229)',
                backgroundColor: 'rgba(30, 136, 229, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                pointBackgroundColor: 'rgb(30, 136, 229)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return labels[context[0].dataIndex];
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Temperature (°C)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
}

// Format date
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

// Format time for chart labels
function formatTime(date) {
    return new Intl.DateTimeFormat('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function fetchTemperatureTrend() {
    const trendContainer = document.getElementById('temperature-trend-container');
    trendContainer.innerHTML = '<div class="loader"></div>';

    fetch('/temperature-trend')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch temperature trend');
            }
            return response.json();
        })
        .then(data => {
            // Create an image element with the signed URL
            const img = document.createElement('img');
            img.src = data.image_url;
            img.alt = 'Temperature Trend Analysis';
            img.className = 'trend-image';
            
            // Add a timestamp caption
            const caption = document.createElement('div');
            caption.className = 'timestamp';
            caption.textContent = `Analysis generated: ${new Date(data.timestamp).toLocaleString()}`;
            
            // Clear the container and add the image and caption
            trendContainer.innerHTML = '';
            trendContainer.appendChild(img);
            trendContainer.appendChild(caption);
        })
        .catch(error => {
            console.error('Error fetching temperature trend:', error);
            trendContainer.innerHTML = `<p>Error loading temperature trend: ${error.message}</p>`;
        });
}

// Initialize the dashboard when page loads
document.addEventListener('DOMContentLoaded', initDashboard);