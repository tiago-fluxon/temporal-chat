"""
Temporal activities for prompt building and validation.

These activities handle prompt construction with injection protection.
"""

from temporalio import activity

from backend.security import PromptGuard, PromptInjectionError
from backend.temporal.activities.document_activities import Document


@activity.defn
async def build_safe_prompt(
    documents: list[Document],
    user_query: str,
    system_instruction: str = None,
    max_chars_per_file: int = 2000,
) -> str:
    """
    Build safe, structured prompt with injection protection.

    Args:
        documents: List of Document objects to include in context
        user_query: User's question/query
        system_instruction: Optional system instruction (uses default if None)
        max_chars_per_file: Maximum characters per document (default: 2000)

    Returns:
        Structured prompt with clear boundaries

    Raises:
        PromptInjectionError: If user query contains injection patterns
    """
    activity.logger.info(f"Building prompt for query: {user_query[:100]}...")

    guard = PromptGuard(strict_mode=True)

    try:
        guard.validate(user_query)
    except PromptInjectionError as e:
        activity.logger.warning(f"Prompt injection detected: {e}")
        raise

    if system_instruction is None:
        system_instruction = (
            "You are a helpful document analysis assistant. "
            "Analyze the provided documents and answer the user's query accurately. "
            "Base your response only on the information in the documents. "
            "If the documents don't contain relevant information, say so."
        )

    valid_documents = [doc for doc in documents if not doc.error]
    error_documents = [doc for doc in documents if doc.error]

    if error_documents:
        activity.logger.warning(f"Skipping {len(error_documents)} documents with errors")

    if not valid_documents:
        activity.logger.error("No valid documents to analyze")
        raise ValueError("No valid documents available for analysis")

    doc_contexts = []
    for doc in valid_documents:
        # Truncate documents to manage token budget
        content = doc.content[:max_chars_per_file]
        if len(doc.content) > max_chars_per_file:
            content += "\n\n[Document truncated...]"

        doc_contexts.append(
            f'<document path="{doc.path}" filename="{doc.filename}" type="{doc.file_type}">\n'
            f"{content}\n"
            f"</document>"
        )

    prompt = guard.build_safe_prompt(
        user_query=user_query,
        documents=doc_contexts,
        system_instruction=system_instruction,
    )

    activity.logger.info(f"Built prompt: {len(valid_documents)} docs, {len(prompt)} chars total")

    return prompt
