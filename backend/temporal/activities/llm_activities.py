"""
Temporal activities for LLM interaction.

Activities signal tokens back to workflow using Temporal's Signal feature.
"""

from temporalio import activity
from temporalio.client import Client

from backend.llm import BaseLLMAdapter, LLMProviderError, create_llm_adapter


class LLMActivities:
    """Activities for LLM streaming using Temporal signals."""

    def __init__(self, llm_adapter: BaseLLMAdapter = None, temporal_client: Client = None):
        """
        Initialize LLM activities.

        Args:
            llm_adapter: LLM adapter (if None, created from env vars)
            temporal_client: Temporal client for signaling workflows
        """
        if llm_adapter is None:
            try:
                self.llm = create_llm_adapter()
            except LLMProviderError as e:
                activity.logger.error(f"Failed to create LLM adapter: {e}")
                raise
        else:
            self.llm = llm_adapter

        self.client = temporal_client

    @activity.defn
    async def stream_llm_native(
        self,
        prompt: str,
        workflow_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict:
        """
        Stream LLM completion with Temporal signals.

        Tokens are sent back to workflow via signals as they're generated.
        Client polls workflow state via Query to receive tokens.

        Args:
            prompt: The prompt to send to LLM
            workflow_id: Workflow ID to send signals to
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 - 1.0)

        Returns:
            Dict with completion stats (token_count, model, etc.)

        Raises:
            ValueError: If prompt is empty
            LLMProviderError: If LLM request fails
        """
        activity.logger.info(
            f"Starting LLM stream to workflow: {workflow_id} "
            f"(provider: {self.llm.provider_name})"
        )

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if self.client is None:
            raise RuntimeError(
                "Temporal client not available. "
                "LLMActivities must be initialized with temporal_client."
            )

        token_count = 0
        finish_reason = None
        batch = []
        batch_size = 5  # Batch tokens to reduce signal overhead

        try:
            handle = self.client.get_workflow_handle(workflow_id)

            async for chunk in self.llm.stream_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                batch.append(chunk.content)
                token_count += 1

                if len(batch) >= batch_size:
                    for token in batch:
                        await handle.signal("receive_token", token)
                    batch = []

                # Heartbeat every 20 tokens to keep activity alive
                if token_count % 20 == 0:
                    activity.heartbeat(f"Streamed {token_count} tokens")

                # Send status update every 50 tokens for UI feedback
                if token_count % 50 == 0:
                    try:
                        await handle.signal(
                            "update_status",
                            f"Generating response... ({token_count} tokens)"
                        )
                    except Exception as e:
                        activity.logger.warning(f"Failed to send status update: {e}")

                if chunk.finish_reason:
                    finish_reason = chunk.finish_reason

            if batch:
                for token in batch:
                    await handle.signal("receive_token", token)

            activity.logger.info(
                f"Completed streaming: {token_count} tokens, "
                f"finish_reason: {finish_reason}"
            )

            return {
                "token_count": token_count,
                "finish_reason": finish_reason,
                "model": self.llm.default_model,
                "provider": self.llm.provider_name,
            }

        except Exception as e:
            activity.logger.error(f"LLM streaming error: {e}")

            # Best effort to signal error back to workflow
            try:
                await handle.signal("update_status", f"Error: {e}")
            except Exception:
                pass

            raise
