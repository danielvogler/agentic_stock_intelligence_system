"""
Callback Logging Module.

This module provides callback functions to log interactions between the agent framework
and the underlying language models. It standardizes the tracing of queries sent to
models and the subsequent responses or function calls they produce.
"""

import logging

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse

logger = logging.getLogger(__name__)


def log_query_to_model(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """
    Log the final user query part sent to the language model.

    Args:
        callback_context (CallbackContext): The execution context containing agent metadata.
        llm_request (LlmRequest): The request payload being sent to the model.
    """
    try:
        if llm_request.contents and llm_request.contents[-1].role == "user":
            for part in llm_request.contents[-1].parts:
                if part.text:
                    logger.info(
                        "[Query to %s]: %s", callback_context.agent_name, part.text
                    )
    except Exception as e:
        logger.debug("Failed to extract or log query to model: %s", e)


def log_model_response(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> None:
    """
    Log the text or function call returned by the language model.

    Args:
        callback_context (CallbackContext): The execution context containing agent metadata.
        llm_response (LlmResponse): The response payload received from the model.
    """
    try:
        if llm_response.content and llm_response.content.parts:
            for part in llm_response.content.parts:
                if part.text:
                    logger.info(
                        "[Response from %s]: %s", callback_context.agent_name, part.text
                    )
                elif part.function_call:
                    logger.info(
                        "[Function call from %s]: %s",
                        callback_context.agent_name,
                        part.function_call.name,
                    )
    except Exception as e:
        logger.debug("Failed to extract or log response from model: %s", e)
