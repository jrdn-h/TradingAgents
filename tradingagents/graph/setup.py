# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.analysts.base_analyst import AnalystAgent
from tradingagents.agents.analysts.fundamentals_analyst import FundamentalsAnalyst
from tradingagents.agents.analysts.market_analyst import MarketAnalyst
from tradingagents.agents.analysts.news_analyst import NewsAnalyst
from tradingagents.agents.analysts.social_media_analyst import SocialMediaAnalyst
from tradingagents.agents.researchers.bull_researcher import BullResearcher
from tradingagents.agents.researchers.bear_researcher import BearResearcher
from tradingagents.agents.managers.research_manager import ResearchManager
from tradingagents.agents.trader.trader import TraderAgent
from tradingagents.agents.managers.risk_manager import RiskManager
from tradingagents.agents.risk_mgmt.aggresive_debator import AggressiveDebator
from tradingagents.agents.risk_mgmt.neutral_debator import NeutralDebator
from tradingagents.agents.risk_mgmt.conservative_debator import ConservativeDebator
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit

from .conditional_logic import ConditionalLogic


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic

        self.analyst_classes = {
            "market": MarketAnalyst,
            "social": SocialMediaAnalyst,
            "news": NewsAnalyst,
            "fundamentals": FundamentalsAnalyst,
        }

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if not selected_analysts:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst instances
        analysts = {
            name: self.analyst_classes[name](self.quick_thinking_llm, self.toolkit)
            for name in selected_analysts
        }
        
        # Create researcher and manager nodes
        bull_researcher_node = BullResearcher(self.quick_thinking_llm, self.bull_memory)
        bear_researcher_node = BearResearcher(self.quick_thinking_llm, self.bear_memory)
        research_manager_node = ResearchManager(self.deep_thinking_llm, self.invest_judge_memory)
        trader_node = TraderAgent(self.deep_thinking_llm)

        # Create risk analysis nodes
        risky_analyst = AggressiveDebator(self.quick_thinking_llm)
        neutral_analyst = NeutralDebator(self.quick_thinking_llm)
        safe_analyst = ConservativeDebator(self.quick_thinking_llm)
        risk_manager_node = RiskManager(self.quick_thinking_llm)

        # Build the graph
        workflow = StateGraph(AgentState)
        
        # Add analyst nodes and tool nodes
        for name, agent in analysts.items():
            workflow.add_node(name, agent.run)
            workflow.add_node(f"tools_{name}", self.tool_nodes[name])
        
        # Add other nodes
        workflow.add_node("bull_researcher", bull_researcher_node.run)
        workflow.add_node("bear_researcher", bear_researcher_node.run)
        workflow.add_node("research_manager", research_manager_node.run)
        workflow.add_node("trader", trader_node.run)
        workflow.add_node("risky_analyst", risky_analyst.run)
        workflow.add_node("neutral_analyst", neutral_analyst.run)
        workflow.add_node("safe_analyst", safe_analyst.run)
        workflow.add_node("risk_manager", risk_manager_node.run)

        # Define edges
        # Start with the first analyst
        first_analyst = selected_analysts[0]
        workflow.add_edge(START, first_analyst)

        # Connect analysts in sequence
        for i, analyst_type in enumerate(selected_analysts):
            current_tools_name = f"tools_{analyst_type}"

            # Add conditional edges for current analyst
            workflow.add_conditional_edges(
                analyst_type,
                self.conditional_logic.should_continue,
                {
                    "continue": "bull_researcher" if i == len(selected_analysts) - 1 else selected_analysts[i+1],
                    "tools": current_tools_name,
                },
            )
            workflow.add_edge(current_tools_name, analyst_type)
        
        # Add remaining edges
        workflow.add_conditional_edges(
            "bull_researcher",
            self.conditional_logic.should_continue_debate,
            {
                "bear_researcher": "bear_researcher",
                "research_manager": "research_manager",
            },
        )
        workflow.add_conditional_edges(
            "bear_researcher",
            self.conditional_logic.should_continue_debate,
            {
                "bull_researcher": "bull_researcher",
                "research_manager": "research_manager",
            },
        )
        workflow.add_edge("research_manager", "trader")
        workflow.add_edge("trader", "risky_analyst")
        workflow.add_conditional_edges(
            "risky_analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "safe_analyst": "safe_analyst",
                "risk_manager": "risk_manager",
            },
        )
        workflow.add_conditional_edges(
            "safe_analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "neutral_analyst": "neutral_analyst",
                "risk_manager": "risk_manager",
            },
        )
        workflow.add_conditional_edges(
            "neutral_analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "risky_analyst": "risky_analyst",
                "risk_manager": "risk_manager",
            },
        )

        workflow.add_edge("risk_manager", END)

        # Compile and return
        return workflow.compile()
