from .base_analyst import AnalystAgent
from ..utils.agent_utils import Toolkit
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import List, Any

class FundamentalsAnalyst(AnalystAgent):
    """
    An analyst agent that specializes in fundamental analysis.
    """
    def __init__(self, llm, toolkit: Toolkit):
        super().__init__("fundamentals_analyst", llm, toolkit)

    def get_tools(self) -> List[Any]:
        """
        Returns the list of tools for the agent.
        """
        if self.toolkit.config["online_tools"]:
            return [self.toolkit.get_fundamentals_openai]
        else:
            return [
                self.toolkit.get_finnhub_company_insider_sentiment,
                self.toolkit.get_finnhub_company_insider_transactions,
                self.toolkit.get_simfin_balance_sheet,
                self.toolkit.get_simfin_cashflow,
                self.toolkit.get_simfin_income_stmt,
            ]

    def get_system_message(self) -> str:
        """
        Returns the system message for the agent's prompt.
        """
        return (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, company financial history, insider sentiment and insider transactions to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
        )

async def fundamentals_analyst_node(state):
    # This is a temporary adapter to make the new class-based agent work with the old graph setup.
    # We will refactor the graph setup later to directly use the agent instances.
    from tradingagents.graph.trading_graph import TradingAgentsGraph  # Local import to avoid circular dependency
    
    # This is not ideal, but for now it's the simplest way to get the LLM and toolkit
    # without a major refactor of the graph.
    graph = TradingAgentsGraph() 
    agent = FundamentalsAnalyst(graph.deep_thinking_llm, graph.toolkit)
    
    result = await agent.run(state)
    
    return {
        "messages": result["messages"],
        "fundamentals_report": result["report"],
    }
