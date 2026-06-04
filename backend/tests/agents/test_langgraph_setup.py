"""LangGraph 集成冒烟测试。"""


def test_langgraph_imports() -> None:
    """验证 LangGraph 核心 API 可 import。"""
    from langgraph.graph import END, START, StateGraph

    assert StateGraph is not None
    assert START is not None
    assert END is not None


def test_langgraph_can_build_graph() -> None:
    """验证可以构建最小图。"""
    from typing import TypedDict

    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        value: int

    def increment(state: State) -> dict[str, int]:
        return {"value": state["value"] + 1}

    graph = StateGraph(State)
    graph.add_node("inc", increment)
    graph.add_edge(START, "inc")
    graph.add_edge("inc", END)
    app = graph.compile()

    result = app.invoke({"value": 0})
    assert result["value"] == 1
