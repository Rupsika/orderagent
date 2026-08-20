"""
agent.py

The ReAct loop from the README, built explicitly with LangGraph so the
think -> act -> observe structure is visible:

    START -> agent(LLM decides) -> [tool_calls?] -> tools -> agent -> ... -> END
                                  \\-> no tool_calls -> END

- "agent" node: Gemini 2.5 Flash (via LangChain) reasons over the
  conversation and either calls a tool or gives a final answer.
- "tools" node: executes whichever tool(s) the LLM asked for and feeds
  the results back in as ToolMessages (the "observation").
- The loop repeats until the LLM responds with no further tool calls.

Swap ChatGoogleGenerativeAI for ChatOpenAI / any other LangChain chat
model in get_llm() without touching the graph logic.
"""

import os
from typing import Annotated, TypedDict, Sequence

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tools import build_tools

SYSTEM_PROMPT = """You are a customer support agent for an e-commerce delivery platform.

Rules:
- You can only see and act on data belonging to the authenticated customer whose tools are provided to you. Never claim to access another customer's data.
- Only call the tools you actually need for this question. Don't call every tool on every turn (e.g. a tracking question doesn't need refund-eligibility).
- If the customer's issue can't be fully resolved with information alone (damaged item, missing delivery, needs a human), create a support ticket instead of promising something you can't do.
- Be concise, direct, and empathetic. Don't expose internal tool names or reasoning steps to the customer — just give the answer.
"""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def get_llm():
    """
    Returns the chat model. Defaults to Gemini 2.5 Flash per the README.
    Requires GOOGLE_API_KEY in the environment (see .env.example).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )


def build_agent(customer_id: str):
    """Compile a LangGraph agent scoped to one authenticated customer."""
    tools = build_tools(customer_id)
    llm_with_tools = get_llm().bind_tools(tools)

    def agent_node(state: AgentState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def route(state: AgentState):
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def run_agent(customer_id: str, user_message: str, history: list[dict] | None = None):
    """
    Run one turn of the agent for a customer.

    `history` is a list of {"role": "human"|"ai", "content": str} dicts as
    persisted in the DB (see crud.get_messages) — only the final human/ai
    text of each past turn is replayed, not the intermediate tool calls,
    since each turn re-runs its own fresh tool loop.

    Returns:
        {
          "response": str,          # final natural-language answer
          "tool_trace": [str, ...], # which tools were called, in order
        }
    """
    app = build_agent(customer_id)

    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in history or []:
        if turn["role"] == "human":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=user_message))

    result = app.invoke({"messages": messages})
    result_messages = result["messages"]

    tool_trace = []
    for m in result_messages:
        if getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tool_trace.append(tc["name"])

    final_response = result_messages[-1].content

    return {
        "response": final_response,
        "tool_trace": tool_trace,
    }
