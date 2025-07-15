from fastapi import FastAPI
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# --- FastAPI app expected by `uvicorn main:app` ---
app = FastAPI(title="TradingAgents API")

@app.get("/")
async def health_check():
    """Basic liveness probe for Docker, Prometheus, Kubernetes, etc."""
    return {"status": "ok"}

# -------------------------------------------------

# Your existing CLI / script logic can still run when you invoke
# `python main.py` directly, but it won't execute on container start‑up.
if __name__ == "__main__":
    tg = TradingAgentsGraph()
    decision = tg.run_trade_decision()
    print("Trade decision:", decision)
