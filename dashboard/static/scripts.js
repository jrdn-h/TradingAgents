let equityChart = null;
        
function updateDashboard(data) {
    // Update status
    document.getElementById('symbol').textContent = data.symbol || '-';
    document.getElementById('tick-count').textContent = data.tick_count || 0;
    document.getElementById('last-update').textContent = data.last_update ? 
        new Date(data.last_update).toLocaleTimeString() : '-';
    
    // Update status indicator
    const statusIndicator = document.getElementById('status-indicator');
    statusIndicator.className = 'status-indicator status-' + (data.status || 'idle');
    statusIndicator.textContent = data.status || 'idle';
    
    // Update price
    const priceElement = document.getElementById('current-price');
    if (data.current_price) {
        priceElement.textContent = '$' + data.current_price.toLocaleString();
    }
    
    // Update technical indicators
    if (data.technical_indicators) {
        document.getElementById('sma').textContent = data.technical_indicators.sma || '-';
        document.getElementById('ema').textContent = data.technical_indicators.ema || '-';
        document.getElementById('breakout').textContent = data.technical_indicators.breakout || '-';
    }
    
    // Update sentiment gauge
    const sentimentScore = document.getElementById('sentiment-score');
    const gaugeNeedle = document.getElementById('gauge-needle');
    if (data.sentiment_index !== undefined) {
        sentimentScore.textContent = data.sentiment_index.toFixed(3);
        
        // Update gauge needle position (-1 to 1 maps to 10 to 110)
        const angle = (data.sentiment_index + 1) * 50; // -1..1 -> 0..100
        const x = 10 + (angle / 100) * 100; // 10..110
        gaugeNeedle.setAttribute('cx', x);
    }
    
    // Update tweet feed
    const tweetFeed = document.getElementById('tweet-feed');
    if (data.tweet_feed && data.tweet_feed.length > 0) {
        tweetFeed.innerHTML = data.tweet_feed.map(tweet => `
            <div class="tweet-item ${tweet.sentiment_label}">
                <div class="tweet-header">
                    <span class="tweet-author">@${tweet.author}</span>
                    <span class="tweet-time">${new Date(tweet.created_at).toLocaleTimeString()}</span>
                </div>
                <div class="tweet-text">${tweet.text}</div>
                <div class="tweet-sentiment">
                    <span class="sentiment-badge sentiment-${tweet.sentiment_label}">${tweet.sentiment_label}</span>
                    <span>Score: ${tweet.sentiment_score.toFixed(3)}</span>
                </div>
                ${tweet.keywords.length > 0 ? `<div class="tweet-keywords">Keywords: ${tweet.keywords.join(', ')}</div>` : ''}
            </div>
        `).join('');
    }
    
    // Update trade decision
    const tradeElement = document.getElementById('trade-decision');
    if (data.trade_decision) {
        tradeElement.textContent = JSON.stringify(data.trade_decision, null, 2);
    }
    
    // Update risk approval
    const riskElement = document.getElementById('risk-approval');
    if (data.risk_approval) {
        riskElement.textContent = JSON.stringify(data.risk_approval, null, 2);
    }
    
    // Update equity chart
    if (data.equity_curve && data.equity_curve.length > 0) {
        updateEquityChart(data.equity_curve);
    }
    
    // Update errors
    const errorsElement = document.getElementById('errors');
    if (data.errors && data.errors.length > 0) {
        errorsElement.innerHTML = data.errors.map(error => 
            `<div class="error">${error}</div>`
        ).join('');
    } else {
        errorsElement.innerHTML = '';
    }
}

function updateEquityChart(equityData) {
    const ctx = document.getElementById('equity-canvas').getContext('2d');
    
    if (equityChart) {
        equityChart.destroy();
    }
    
    const labels = equityData.map(point => point.tick);
    const data = equityData.map(point => point.equity);
    
    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Equity',
                data: data,
                borderColor: '#27ae60',
                backgroundColor: 'rgba(39, 174, 96, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
}

async function fetchStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// Connect to SSE stream
const eventSource = new EventSource('/stream');

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};

eventSource.onerror = function(event) {
    console.error('SSE connection error:', event);
    // Fallback to polling if SSE fails
    setInterval(fetchStatus, 2000);
};

// Initial load
fetchStatus(); 