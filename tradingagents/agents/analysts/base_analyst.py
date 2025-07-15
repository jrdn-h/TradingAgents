from abc import abstractmethod
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from ..base_agent import BaseAgent
from ..utils.agent_utils import Toolkit

class AnalystAgent(BaseAgent):
    """
    Base class for analyst agents that use LangChain tools.
    """

    def __init__(self, name: str, llm, toolkit: Toolkit):
        super().__init__(name)
        self.llm = llm
        self.toolkit = toolkit

    @abstractmethod
    def get_tools(self) -> List[Any]:
        """
        Returns the list of tools for the agent.
        """
        pass

    @abstractmethod
    def get_system_message(self) -> str:
        """
        Returns the system message for the agent's prompt.
        """
        pass

    def get_prompt(self) -> ChatPromptTemplate:
        """
        Creates and returns the prompt for the agent.
        """
        tools = self.get_tools()
        system_message = self.get_system_message()

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        return prompt

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the agent and returns the result.
        """
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        prompt = self.get_prompt()
        prompt = prompt.partial(current_date=current_date, ticker=ticker)

        tools = self.get_tools()
        chain = prompt | self.llm.bind_tools(tools)
        
        result = chain.invoke(state["messages"])
        
        report = ""
        if not result.tool_calls:
            report = result.content
            
        return {
            "messages": [result],
            "report": report,
        } 