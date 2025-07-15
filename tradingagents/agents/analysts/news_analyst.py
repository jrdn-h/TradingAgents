from .base_analyst import AnalystAgent
from ..utils.agent_utils import Toolkit
from typing import List, Any

class NewsAnalyst(AnalystAgent):
    """
    An analyst agent that specializes in news analysis.
    """
    def __init__(self, llm, toolkit: Toolkit):
        super().__init__("news_analyst", llm, toolkit)

    def get_tools(self) -> List[Any]:
        """
        Returns the list of tools for the agent.
        """
        if self.toolkit.config["online_tools"]:
            return [self.toolkit.get_global_news_openai, self.toolkit.get_google_news]
        else:
            return [
                self.toolkit.get_finnhub_news,
                self.toolkit.get_reddit_news,
                self.toolkit.get_google_news,
            ]

    def get_system_message(self) -> str:
        """
        Returns the system message for the agent's prompt.
        """
        return (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Look at news from EODHD, and finnhub to be comprehensive. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
        )

async def news_analyst_node(state):
    # This is a temporary adapter to make the new class-based agent work with the old graph setup.
    from tradingagents.graph.trading_graph import TradingAgentsGraph  # Local import to avoid circular dependency
    
    graph = TradingAgentsGraph() 
    agent = NewsAnalyst(graph.deep_thinking_llm, graph.toolkit)
    
    result = await agent.run(state)
    
    return {
        "messages": result["messages"],
        "news_report": result["report"],
    }
