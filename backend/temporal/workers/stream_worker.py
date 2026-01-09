"""
Temporal Worker for LLM Chat Workflows.

This worker:
1. Connects to Temporal server
2. Registers workflows and activities
3. Polls for tasks and executes them
"""

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from backend.llm import create_llm_adapter
# Import activities directly to avoid triggering __init__.py which imports httpx (blocked by Temporal sandbox)
from backend.temporal.activities.document_activities import (
    read_document,
    scan_directory,
)
from backend.temporal.activities.prompt_activities import build_safe_prompt
from backend.temporal.activities.llm_activities import LLMActivities
from backend.temporal.workflows import LLMChatWorkflow


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the Temporal worker."""

    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TASK_QUEUE", "chat-queue")

    logger.info("=" * 60)
    logger.info("Starting Temporal Worker")
    logger.info("=" * 60)

    logger.info("Initializing LLM adapter")
    try:
        llm_adapter = create_llm_adapter()
        logger.info(
            f"✓ LLM adapter created: {llm_adapter.provider_name} "
            f"({llm_adapter.default_model})"
        )
    except Exception as e:
        logger.error(f"✗ LLM adapter creation failed: {e}")
        raise

    # Connect to Temporal before creating LLM activities (client needed for signaling)
    logger.info(f"Connecting to Temporal: {temporal_address}")
    try:
        temporal_client = await Client.connect(
            temporal_address,
            namespace=temporal_namespace,
        )
        logger.info("✓ Temporal connection successful")
    except Exception as e:
        logger.error(f"✗ Temporal connection failed: {e}")
        raise

    llm_activities = LLMActivities(
        llm_adapter=llm_adapter,
        temporal_client=temporal_client,
    )

    # Allow httpx in sandbox - it's only used in activities, not workflows
    logger.info(f"Creating worker on task queue: {task_queue}")

    custom_restrictions = SandboxRestrictions.default.with_passthrough_modules(
        # HTTP clients and related modules
        "httpx",
        "httpcore",
        "urllib.request",
        "urllib3",
        "ssl",
        "h11",
        # Async libraries used by AI SDKs
        "anyio",
        "sniffio",
        # AI SDK modules (only used in activities, not workflows)
        "openai",
        "anthropic",
    )

    worker = Worker(
        temporal_client,
        task_queue=task_queue,
        workflows=[LLMChatWorkflow],
        activities=[
            # Document activities
            scan_directory,
            read_document,
            # Prompt activities
            build_safe_prompt,
            # LLM activities
            llm_activities.stream_llm_native,
        ],
        workflow_runner=SandboxedWorkflowRunner(restrictions=custom_restrictions),
    )

    logger.info("=" * 60)
    logger.info("Worker Configuration")
    logger.info("=" * 60)
    logger.info(f"Temporal Address: {temporal_address}")
    logger.info(f"Namespace: {temporal_namespace}")
    logger.info(f"Task Queue: {task_queue}")
    logger.info(f"LLM Provider: {llm_adapter.provider_name}")
    logger.info(f"LLM Model: {llm_adapter.default_model}")
    logger.info("=" * 60)
    logger.info("Worker is running! Waiting for workflows...")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    # Run worker (blocks until interrupted)
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received")
    finally:
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
