# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue(self, state: AgentState) -> str:
        """
        Determines the next step after an analyst node.
        If the last message has tool calls, it routes to the tool node.
        Otherwise, it continues to the next step in the graph.
        """
        if state["messages"][-1].tool_calls:
            return "tools"
        return "continue"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""

        if (
            state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds
        ):  # 3 rounds of back-and-forth between 2 agents
            return "research_manager"
        if state["investment_debate_state"]["current_response"].startswith("Bull"):
            return "bear_researcher"
        return "bull_researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        if (
            state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):  # 3 rounds of back-and-forth between 3 agents
            return "risk_manager"
        if state["risk_debate_state"]["latest_speaker"].startswith("Risky"):
            return "safe_analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Safe"):
            return "neutral_analyst"
        return "risky_analyst"
