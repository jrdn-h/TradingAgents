# TradingAgents Grafana/Prometheus Setup

This guide sets up live monitoring for your TradingAgents system with Prometheus metrics collection and Grafana dashboards.

## Quick Start

### 1. Start the Full Stack

```bash
# Start all services (TradingAgents, Prometheus, Grafana)
docker compose up -d

# Check all services are running
docker compose ps
```

### 2. Access the Dashboards

- **Grafana Dashboard**: http://localhost:3000
  - Username: `admin`
  - Password: `changeme`
  - The TradingAgents dashboard will be automatically loaded

- **Prometheus Console**: http://localhost:9090
  - Check Status → Targets to verify TradingAgents is UP

- **TradingAgents Dashboard**: http://localhost:8001
  - Your existing FastAPI dashboard

### 3. Test the Metrics

```bash
# Run a replay to populate metrics
poetry run python -m tradingagents replay \
  --from 2024-01-01 --to 2024-01-02 \
  --symbol BTCUSD --tweets sample_tweets.csv --plot

# Ingest some demo tweets
curl -X POST http://localhost:8001/ingest-tweet \
  -H "X-API-Key: demo-key-123" \
  -H "Content-Type: application/json" \
  -d '{"tweet_text": "Bitcoin is mooning! 🚀", "author": "test_user"}'
```

## Dashboard Panels

The Grafana dashboard includes:

### Live Metrics
- **Tweet Rate**: Real-time tweets per minute
- **Sentiment Index**: Current sentiment gauge (-1 to +1)
- **Rate Limit Backoffs**: 429 error tracking

### Backtest Performance
- **Sharpe Ratio**: Last replay Sharpe ratio
- **Win Rate**: Last replay win percentage
- **Max Drawdown**: Last replay maximum drawdown
- **Sentiment Correlation**: Sentiment-price correlation trend

## Configuration Files

- `docker-compose.yml`: Service definitions
- `prometheus.yml`: Prometheus scraping configuration
- `grafana/provisioning/`: Auto-loaded datasources and dashboards

## Troubleshooting

### Prometheus Targets Down
```bash
# Check if TradingAgents is exposing metrics
curl http://localhost:8001/metrics

# Check Prometheus logs
docker compose logs prometheus
```

### Grafana Dashboard Empty
1. Verify Prometheus datasource is connected
2. Check that metrics are being scraped
3. Run a replay or ingest tweets to generate data

### Metrics Not Updating
```bash
# Check if prometheus-client is installed
poetry show prometheus-client

# Verify metrics are being exposed
curl http://localhost:8001/metrics | grep tradingagents
```

## Customization

### Add New Metrics
1. Add gauges to `tradingagents/backtest/metrics.py`
2. Update the dashboard JSON in `grafana/provisioning/dashboards/`
3. Restart the stack: `docker compose restart`

### Alerting
1. In Grafana, go to Alerting → Alert Rules
2. Create rules based on metrics like:
   - `replay_sharpe_last < 0` (poor performance)
   - `rate(backoffs_total[5m]) > 0.1` (too many rate limits)

## Production Notes

- Change default passwords in production
- Use persistent volumes for data retention
- Set up proper authentication for Grafana
- Configure alerting notifications (email, Slack, etc.)
- Monitor resource usage of the stack 