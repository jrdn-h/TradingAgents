from .base_analyst import AnalystAgent
from ..utils.agent_utils import Toolkit
from typing import List, Any

class SocialMediaAnalyst(AnalystAgent):
    """
    An analyst agent that specializes in social media analysis.
    """
    def __init__(self, llm, toolkit: Toolkit):
        super().__init__("social_media_analyst", llm, toolkit)

    def get_tools(self) -> List[Any]:
        """
        Returns the list of tools for the agent.
        """
        if self.toolkit.config["online_tools"]:
            return [self.toolkit.get_stock_news_openai]
        else:
            return [
                self.toolkit.get_reddit_stock_info,
            ]

    def get_system_message(self) -> str:
        """
        Returns the system message for the agent's prompt.
        """
        return (
            "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Try to look at all sources possible from social media to sentiment to news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
        )

async def social_media_analyst_node(state):
    # This is a temporary adapter to make the new class-based agent work with the old graph setup.
    from tradingagents.graph.trading_graph import TradingAgentsGraph  # Local import to avoid circular dependency
    
    graph = TradingAgentsGraph()
    agent = SocialMediaAnalyst(graph.deep_thinking_llm, graph.toolkit)
    
    result = await agent.run(state)
    
    return {
        "messages": result["messages"],
        "sentiment_report": result["report"],
    }
