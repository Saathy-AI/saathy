"""
Context Orchestration Graph - The brain of the agentic system.
Manages the flow between different agents to intelligently gather and evaluate context.
"""

import logging
from datetime import datetime
from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .context_expander import ContextExpanderAgent
from .context_retriever import ContextRetrieverAgent
from .information_analyzer import InformationAnalyzerAgent
from .response_generator import ResponseGeneratorAgent
from .sufficiency_evaluator import SufficiencyEvaluatorAgent

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """State that flows through the graph"""

    # Input
    user_message: str
    session_id: str
    user_id: str
    conversation_history: list[dict[str, Any]]

    # Processing state
    information_needs: Optional[dict[str, Any]]
    retrieved_context: Optional[dict[str, Any]]
    sufficiency_score: Optional[float]
    sufficiency_gaps: Optional[list[str]]
    expansion_attempts: int

    # Output
    final_response: Optional[str]
    context_used: Optional[dict[str, Any]]
    metadata: dict[str, Any]


class ContextOrchestrationGraph:
    """
    Multi-agent system using LangGraph for intelligent context orchestration.
    This is where the real intelligence lives - agents work together to:
    1. Understand what the user needs
    2. Retrieve relevant context
    3. Evaluate if context is sufficient
    4. Expand context if needed
    5. Generate intelligent responses
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.max_expansion_attempts = config.get("max_expansion_attempts", 3)

        # Initialize agents
        self.information_analyzer = InformationAnalyzerAgent(config)
        self.context_retriever = ContextRetrieverAgent(config)
        self.sufficiency_evaluator = SufficiencyEvaluatorAgent(config)
        self.context_expander = ContextExpanderAgent(config)
        self.response_generator = ResponseGeneratorAgent(config)

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""

        # Create the graph
        workflow = StateGraph(GraphState)

        # Add nodes (each node is an agent)
        workflow.add_node("analyze", self._analyze_information_needs)
        workflow.add_node("retrieve", self._retrieve_context)
        workflow.add_node("evaluate", self._evaluate_sufficiency)
        workflow.add_node("expand", self._expand_context)
        workflow.add_node("generate", self._generate_response)

        # Define the flow
        workflow.set_entry_point("analyze")

        # After analyzing, always retrieve context
        workflow.add_edge("analyze", "retrieve")

        # After retrieving, evaluate sufficiency
        workflow.add_edge("retrieve", "evaluate")

        # Conditional edge: expand or generate based on sufficiency
        workflow.add_conditional_edges(
            "evaluate",
            self._should_expand_context,
            {
                "expand": "expand",
                "generate": "generate",
            },
        )

        # After expansion, retrieve again
        workflow.add_edge("expand", "retrieve")

        # Generate response leads to end
        workflow.add_edge("generate", END)

        return workflow.compile()

    async def _analyze_information_needs(self, state: GraphState) -> GraphState:
        """Analyze user query to understand information needs"""
        logger.info(f"Analyzing information needs for session {state['session_id']}")

        information_needs = await self.information_analyzer.analyze(
            user_message=state["user_message"],
            conversation_history=state.get("conversation_history", []),
            user_id=state["user_id"],
        )

        state["information_needs"] = information_needs
        state["metadata"]["analysis_timestamp"] = datetime.utcnow().isoformat()

        logger.info(f"Identified needs: {information_needs.get('intent', 'unknown')}")
        return state

    async def _retrieve_context(self, state: GraphState) -> GraphState:
        """Retrieve context based on information needs"""
        logger.info(f"Retrieving context for session {state['session_id']}")

        # Check if this is an expansion attempt
        is_expansion = state.get("expansion_attempts", 0) > 0

        retrieved_context = await self.context_retriever.retrieve(
            information_needs=state["information_needs"],
            user_id=state["user_id"],
            expansion_hints=state.get("sufficiency_gaps", []) if is_expansion else None,
        )

        state["retrieved_context"] = retrieved_context
        state["metadata"]["retrieval_timestamp"] = datetime.utcnow().isoformat()
        state["metadata"]["context_size"] = len(
            retrieved_context.get("all_results", [])
        )

        logger.info(
            f"Retrieved {len(retrieved_context.get('all_results', []))} context items"
        )
        return state

    async def _evaluate_sufficiency(self, state: GraphState) -> GraphState:
        """Evaluate if retrieved context is sufficient"""
        logger.info(f"Evaluating context sufficiency for session {state['session_id']}")

        evaluation = await self.sufficiency_evaluator.evaluate(
            query=state["user_message"],
            context=state["retrieved_context"],
            information_needs=state["information_needs"],
        )

        state["sufficiency_score"] = evaluation["score"]
        state["sufficiency_gaps"] = evaluation.get("gaps", [])
        state["metadata"]["sufficiency_evaluation"] = evaluation

        logger.info(f"Sufficiency score: {evaluation['score']:.2f}")
        return state

    async def _expand_context(self, state: GraphState) -> GraphState:
        """Expand context based on sufficiency gaps"""
        logger.info(f"Expanding context for session {state['session_id']}")

        # Increment expansion attempts
        state["expansion_attempts"] = state.get("expansion_attempts", 0) + 1

        # Plan expansion strategy
        expansion_plan = await self.context_expander.plan_expansion(
            current_context=state["retrieved_context"],
            information_needs=state["information_needs"],
            sufficiency_gaps=state["sufficiency_gaps"],
            attempt_number=state["expansion_attempts"],
        )

        # Update information needs with expansion hints
        state["information_needs"].update(expansion_plan)
        state["metadata"][f"expansion_attempt_{state['expansion_attempts']}"] = (
            expansion_plan
        )

        logger.info(
            f"Expansion attempt {state['expansion_attempts']}: {expansion_plan.get('strategy', 'unknown')}"
        )
        return state

    async def _generate_response(self, state: GraphState) -> GraphState:
        """Generate final response using retrieved context"""
        logger.info(f"Generating response for session {state['session_id']}")

        response_data = await self.response_generator.generate(
            query=state["user_message"],
            context=state["retrieved_context"],
            information_needs=state["information_needs"],
            conversation_history=state.get("conversation_history", []),
            sufficiency_score=state.get("sufficiency_score", 0.0),
        )

        state["final_response"] = response_data["response"]
        state["context_used"] = response_data["context_used"]
        state["metadata"]["response_timestamp"] = datetime.utcnow().isoformat()
        state["metadata"]["tokens_used"] = response_data.get("tokens_used", 0)

        logger.info(
            f"Generated response with {len(state['context_used'])} context items"
        )
        return state

    def _should_expand_context(self, state: GraphState) -> str:
        """Decide whether to expand context or generate response"""

        # Check sufficiency score
        sufficiency_score = state.get("sufficiency_score", 0.0)
        expansion_attempts = state.get("expansion_attempts", 0)

        # Expansion logic
        if sufficiency_score < 0.7 and expansion_attempts < self.max_expansion_attempts:
            logger.info(
                f"Expanding context (score: {sufficiency_score:.2f}, attempts: {expansion_attempts})"
            )
            return "expand"
        else:
            logger.info(
                f"Proceeding to generation (score: {sufficiency_score:.2f}, attempts: {expansion_attempts})"
            )
            return "generate"

    async def process_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        conversation_history: list[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Main entry point for processing a user message through the graph.

        Returns:
            Dict containing:
            - response: The generated response
            - context_used: What context was used
            - metadata: Processing metadata (timings, scores, etc.)
        """

        # Initialize state
        initial_state: GraphState = {
            "user_message": user_message,
            "session_id": session_id,
            "user_id": user_id,
            "conversation_history": conversation_history or [],
            "information_needs": None,
            "retrieved_context": None,
            "sufficiency_score": None,
            "sufficiency_gaps": None,
            "expansion_attempts": 0,
            "final_response": None,
            "context_used": None,
            "metadata": {},
        }

        # Run the graph
        try:
            final_state = await self.graph.ainvoke(initial_state)

            return {
                "response": final_state["final_response"],
                "context_used": final_state["context_used"],
                "metadata": final_state["metadata"],
            }
        except Exception as e:
            logger.error(f"Error in graph processing: {str(e)}", exc_info=True)
            raise
