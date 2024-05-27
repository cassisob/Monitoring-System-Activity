var transaction_to_send = {{simulate_transactions | safe}};
let currentIndex = 0;

async function send_data() {

    if (currentIndex >= transaction_to_send.length) {
        console.log("All data has been sent.");
        return;
    }
    
    const item = transaction_to_send[currentIndex];
    currentIndex++;

    var response = await fetch('/receive', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(item)
    });

    const data = await response;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

async function updateCharts() {

    var response = await fetch('/', {
        method: 'POST'
    });

    const data = await response.json();

    const timestampsFailed = data.Failed.map(entry => formatTime(entry[0]));
    const timestampsReversed = data.Reversed.map(entry => formatTime(entry[0]));
    const timestampsDenied = data.Denied.map(entry => formatTime(entry[0]));

    updateChart('plotTipo1', data.Failed, data.Anomalies.Failed, 'Failed', timestampsFailed);
    updateChart('plotTipo2', data.Reversed, data.Anomalies.Reversed, 'Reversed', timestampsReversed);
    updateChart('plotTipo3', data.Denied, data.Anomalies.Denied, 'Denied', timestampsDenied);

    const failed_trend = data.Trend.Failed;
    const reversed_trend = data.Trend.Reversed;
    const denied_trend = data.Trend.Denied;

    const failed_total = +data.Overall.Failed;
    const reversed_total = +data.Overall.Reversed;
    const denied_total = +data.Overall.Denied;

    document.getElementById('qtdTipo1').textContent = failed_total;
    document.getElementById('qtdTipo2').textContent = reversed_total;
    document.getElementById('qtdTipo3').textContent = denied_total;

    document.getElementById('anomaliasTipo1').textContent = data.Anomalies.Failed.length;
    document.getElementById('anomaliasTipo2').textContent = data.Anomalies.Reversed.length;
    document.getElementById('anomaliasTipo3').textContent = data.Anomalies.Denied.length;

    document.getElementById('totalQtd').textContent = failed_total + reversed_total + denied_total;
    document.getElementById('totalAnomalias').textContent = data.Anomalies.Failed.length +
                                                                data.Anomalies.Reversed.length +
                                                                data.Anomalies.Denied.length;

    updateTrends(failed_trend, 'iconTipo1', 'trendTipo1');
    updateTrends(reversed_trend, 'iconTipo2', 'trendTipo2');
    updateTrends(denied_trend, 'iconTipo3', 'trendTipo3');
}

function updateChart(container, data, anomalias, name, timestamps) {

    const trace1 = {
        x: timestamps,
        y: data.map(entry => entry[1]),
        type: 'scatter',
        mode: 'lines+markers',
        name: name,
        line: { color: '#1f77b4' }
    };

    const trace2 = {
        x: anomalias.map(entry => formatTime(entry[0])),
        y: anomalias.map(entry => entry[1]),
        mode: 'markers',
        name: 'Anomalies',
        marker: { color: '#d62728', size: 10 }
    };

    const layout = {
        title: {
            text: name,
            font: {
                family: 'Roboto, sans-serif',
                size: 20,
                color: '#ffffff',
                weight: 'bold',
                margin: 0
            }
        },
        paper_bgcolor: '#2b2b2b',
        plot_bgcolor: '#2b2b2b',
        font: {
            color: '#dcdcdc'
        },
        xaxis: {
            title: 'Timeline',
            tickmode: 'linear'
        },
        yaxis: {
            title: 'Quantity'
        },
        showlegend: false
    };

    Plotly.newPlot(container, [trace1, trace2], layout, { responsive: true, margin: 0 });
}

function updateTrends(trend_value, iconId, trendId) {
    const icon = document.getElementById(iconId);
    const trend = document.getElementById(trendId);

    if (trend_value == 2) {
        icon.className = 'fa-solid fa-arrow-up fa-beat fa-xl';
        trend.textContent = 'Rising a lot';
    } else if (trend_value == 1) {
        icon.className = 'fa-solid fa-arrow-trend-up fa-beat fa-xl';
        trend.textContent = 'Rising';
    } else if (trend_value == 0) {
        icon.className = 'fa-solid fa-arrow-right fa-beat fa-xl';
        trend.textContent = 'Stable';
    } else if (trend_value == -1) {
        icon.className = 'fa-solid fa-arrow-trend-down fa-beat fa-xl';
        trend.textContent = 'Falling';
    } else {
        icon.className = 'fa-solid fa-arrow-down fa-beat fa-xl';
        trend.textContent = 'Falling a lot';
    }
}

setInterval(() => {
    updateCharts();
}, 100);

setInterval(() => {
    send_data();
}, 100);

updateCharts();
send_data();