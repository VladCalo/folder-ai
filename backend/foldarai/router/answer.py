"""Router: given a user's question, decides whether to run the financial
tool (tools.run_financial_tool), the semantic tool (tools.run_semantic_tool),
or both, then synthesizes one final answer with citations - or refuses if
nothing grounds an answer. Implements the two-tool design from
docs/01-architecture.md's query pipeline.

DELIBERATELY NOT LangGraph/a ReAct agent for this first pass: a fixed
three-step pipeline (route decision -> run selected tool(s) -> synthesize)
covers every documented example query in docs/02-mvp-scope.md except the
hardest compound case (see the note below), without needing an actual agent
loop. This is a simplification worth revisiting - see
backend/README.md "Deferred: Onyx and Unstract" and the
docs/01-architecture.md router design this stands in for.

KNOWN LIMITATION - true sequential compound questions: "which contracts
were active during our best month" needs the semantic search query itself
to depend on the financial tool's *result* (which month), decided only
after that tool runs. This router picks both tools' queries up front in one
routing call, so it can't do that - the semantic_query for a question like
that will be under-specified. This is exactly the kind of multi-step
tool-calling a real agent loop (LangGraph, per the original design) handles
naturally. Come back to this once the LangGraph router is worth building
for real - flagged here rather than silently accepted.
"""
import json

import psycopg

from . import tools
from .sql_safety import SqlSafetyError
from ..config import Settings
from ..llm_client import OpenRouterError, call_structured
from ..prompts import ROUTE_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT
from ..schema import ROUTE_JSON_SCHEMA, SYNTHESIS_JSON_SCHEMA, RouteDecision, RouterAnswer


def _decide_route(question: str, settings: Settings) -> RouteDecision:
    data = call_structured(ROUTE_SYSTEM_PROMPT, question, ROUTE_JSON_SCHEMA, settings)
    return RouteDecision.model_validate(data)


def answer_question(question: str, conn, settings: Settings) -> RouterAnswer:
    route = _decide_route(question, settings)

    financial_result = None
    if route.use_financial_tool:
        try:
            financial_result = tools.run_financial_tool(
                route.financial_question or question, conn, settings
            )
        except (SqlSafetyError, OpenRouterError, psycopg.Error) as exc:
            # A generated query can be syntactically fine (passes
            # sql_safety's check) but semantically wrong - e.g. it
            # referenced a table/column that doesn't exist. That's a real
            # failure mode we hit in testing (the model invented a `tenants`
            # table), not hypothetical - must not crash the whole answer.
            conn.rollback()  # failed query leaves the transaction aborted
            financial_result = {"error": str(exc)}

    semantic_result = None
    if route.use_semantic_tool:
        try:
            semantic_result = tools.run_semantic_tool(
                route.semantic_query or question, conn, settings
            )
        except (OpenRouterError, psycopg.Error) as exc:
            conn.rollback()
            semantic_result = {"error": str(exc)}

    synthesis_input = json.dumps(
        {
            "question": question,
            "financial_result": financial_result,
            "semantic_result": semantic_result,
        },
        default=str,
    )
    data = call_structured(
        SYNTHESIS_SYSTEM_PROMPT, synthesis_input, SYNTHESIS_JSON_SCHEMA, settings
    )
    return RouterAnswer.model_validate(data)
