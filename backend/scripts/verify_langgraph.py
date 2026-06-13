"""验证 LangGraph 能调 LlamaIndex 抽象层。

用法：
    cd backend
    uv run python scripts/verify_langgraph.py
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.services.llm import get_llm


class State(TypedDict):
    query: str
    response: str


def call_llm(state: State) -> dict[str, str]:
    llm = get_llm()
    response = llm.complete(f"用一句话回答：{state['query']}")
    return {"response": response.text}


def build_graph() -> CompiledStateGraph[State, None, State, State]:
    graph = StateGraph(State)
    graph.add_node("call_llm", call_llm)
    graph.add_edge(START, "call_llm")
    graph.add_edge("call_llm", END)
    return graph.compile()


def main() -> None:
    app = build_graph()
    result = app.invoke({"query": "什么是 RAG？", "response": ""})
    print("LangGraph + LlamaIndex 集成验证：")  # noqa: T201
    print(f"  Query: {result['query']}")  # noqa: T201
    print(f"  Response: {result['response'][:100]}...")  # noqa: T201


if __name__ == "__main__":
    main()
