import pytest
from unittest.mock import patch, MagicMock
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.config import settings

@patch('tradingagents.graph.trading_graph.ChatOpenAI')
@patch('tradingagents.graph.trading_graph.FinancialSituationMemory')
def test_trading_agents_graph_instantiation(mock_financial_situation_memory, mock_chat_openai):
    """
    Tests that the TradingAgentsGraph class can be instantiated without errors.
    """
    graph = TradingAgentsGraph()
    assert graph is not None

@patch('tradingagents.graph.trading_graph.ChatOpenAI')
@patch('tradingagents.graph.trading_graph.FinancialSituationMemory')
def test_trading_agents_graph_config(mock_financial_situation_memory, mock_chat_openai):
    """
    Tests that the TradingAgentsGraph class correctly uses the Pydantic settings.
    """
    graph = TradingAgentsGraph()
    assert graph.config["llm_provider"] == settings.llm_provider
    assert graph.config["deep_think_llm"] == settings.deep_think_llm
    assert graph.config["quick_think_llm"] == settings.quick_think_llm

@pytest.mark.asyncio
@patch('tradingagents.graph.trading_graph.ChatOpenAI')
@patch('tradingagents.graph.trading_graph.FinancialSituationMemory')
async def test_trading_agents_graph_propagate(mock_financial_situation_memory, mock_chat_openai):
    """
    Tests the propagate method of the TradingAgentsGraph class.
    """
    # Patch the propagate method to avoid actual execution
    with patch.object(TradingAgentsGraph, 'propagate', return_value=({"final_trade_decision": "BUY"}, "BUY")) as mock_propagate:
        graph = TradingAgentsGraph(selected_analysts=["market"]) # Use only one analyst to speed up the test
        final_state, decision = graph.propagate("AAPL", "2024-01-02")
    
    assert final_state is not None
    assert decision is not None
    assert isinstance(final_state, dict)
    assert "final_trade_decision" in final_state
    assert final_state["final_trade_decision"] is not None
    mock_propagate.assert_called_once_with("AAPL", "2024-01-02") 