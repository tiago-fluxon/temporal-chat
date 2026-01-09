"""
Main LLM Chat Workflow.

Uses Signal+Query pattern for streaming tokens.
Activities signal tokens back to workflow, clients poll workflow state via Query.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import directly to avoid triggering LLMActivities which uses httpx (blocked by Temporal sandbox)
from backend.temporal.activities.document_activities import Document


@dataclass
class ChatRequest:
    """Request for chat workflow."""

    user_query: str
    doc_path: str
    max_files: int = 10  # Reduced from 50 to prevent token limit issues
    max_file_size_mb: int = 10
    max_chars_per_file: int = 2000  # Limit chars per file to manage token budget
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7


@dataclass
class ChatResult:
    """Result from chat workflow."""

    success: bool
    files_found: int
    files_processed: int
    token_count: int
    model: str
    error: str = ""


@dataclass
class StreamState:
    """Current state of the stream for client polling."""

    tokens: List[str] = field(default_factory=list)
    status: str = "initializing"
    completed: bool = False
    error: Optional[str] = None
    files_found: int = 0
    files_processed: int = 0


@workflow.defn
class LLMChatWorkflow:
    """
    LLM Chat workflow with Temporal streaming.

    Flow:
    1. Scan directory for documents
    2. Read documents in parallel
    3. Build safe prompt
    4. Stream LLM response (activity signals tokens back)
    5. Expose state via Query for client polling

    Streaming:
    - Activity signals tokens via 'receive_token' signal
    - Client polls 'get_stream_state' query every 100-200ms
    """

    def __init__(self):
        """Initialize workflow state."""
        self.state = StreamState()

    @workflow.signal
    async def receive_token(self, token: str) -> None:
        """
        Receive a token from the LLM activity.

        Called by activity as it streams tokens.

        Args:
            token: Single token from LLM
        """
        self.state.tokens.append(token)

    @workflow.signal
    async def update_status(self, status: str) -> None:
        """
        Update workflow status.

        Called by activities to report progress.

        Args:
            status: Status message (e.g., "Scanning files...", "Generating response...")
        """
        self.state.status = status

    @workflow.query
    def get_stream_state(self) -> StreamState:
        """
        Get current stream state for client polling.

        Returns:
            Current state including tokens, status, and completion
        """
        return self.state

    @workflow.query
    def get_tokens_since(self, index: int) -> List[str]:
        """
        Get tokens since a specific index.

        More efficient for clients that track their position.

        Args:
            index: Starting index (exclusive)

        Returns:
            List of tokens from index to current
        """
        return self.state.tokens[index:]

    @workflow.run
    async def run(self, request: ChatRequest) -> ChatResult:
        """
        Execute chat workflow with streaming.

        Args:
            request: ChatRequest with query and configuration

        Returns:
            ChatResult with completion stats
        """
        workflow_id = workflow.info().workflow_id
        workflow.logger.info(
            f"Starting workflow: query='{request.user_query[:50]}...', "
            f"path='{request.doc_path}'"
        )

        try:
            self.state.status = "Scanning directory..."
            workflow.logger.info("Scanning directory")

            file_paths = await workflow.execute_activity(
                "scan_directory",
                args=[request.doc_path, None, 100],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            if not file_paths:
                workflow.logger.warning("No files found")
                self.state.error = "No files found in specified directory"
                self.state.completed = True
                self.state.status = "Failed: No files found"

                return ChatResult(
                    success=False,
                    files_found=0,
                    files_processed=0,
                    token_count=0,
                    model="",
                    error="No files found in specified directory",
                )

            if len(file_paths) > request.max_files:
                workflow.logger.info(f"Limiting to {request.max_files} files")
                file_paths = file_paths[: request.max_files]

            self.state.files_found = len(file_paths)
            workflow.logger.info(f"Found {len(file_paths)} files")

            self.state.status = f"Reading {len(file_paths)} files..."
            workflow.logger.info("Reading documents")

            read_tasks = [
                workflow.execute_activity(
                    "read_document",
                    args=[file_path, request.max_file_size_mb],
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )
                for file_path in file_paths
            ]

            documents_raw = await asyncio.gather(*read_tasks)
            documents = [
                Document(**doc) if isinstance(doc, dict) else doc for doc in documents_raw
            ]
            valid_docs = [doc for doc in documents if not doc.error]

            self.state.files_processed = len(valid_docs)
            workflow.logger.info(f"Read {len(valid_docs)}/{len(documents)} documents")

            if not valid_docs:
                self.state.error = "Failed to read any documents"
                self.state.completed = True
                self.state.status = "Failed: No readable documents"

                return ChatResult(
                    success=False,
                    files_found=len(file_paths),
                    files_processed=0,
                    token_count=0,
                    model="",
                    error="Failed to read any documents",
                )

            self.state.status = "Building prompt..."
            workflow.logger.info("Building prompt")

            prompt = await workflow.execute_activity(
                "build_safe_prompt",
                args=[valid_docs, request.user_query, None, request.max_chars_per_file],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            self.state.status = "Generating response..."
            workflow.logger.info("Streaming LLM response")

            llm_result = await workflow.execute_activity(
                "stream_llm_native",
                args=[
                    prompt,
                    workflow_id,
                    request.llm_max_tokens,
                    request.llm_temperature,
                ],
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            self.state.completed = True
            self.state.status = "Completed"

            workflow.logger.info(
                f"Workflow completed: {llm_result['token_count']} tokens streamed"
            )

            return ChatResult(
                success=True,
                files_found=len(file_paths),
                files_processed=len(valid_docs),
                token_count=llm_result["token_count"],
                model=llm_result["model"],
            )

        except Exception as e:
            actual_error = e.__cause__ if hasattr(e, '__cause__') and e.__cause__ else e
            error_message = str(actual_error)

            workflow.logger.error(f"Workflow error: {error_message}")

            if isinstance(self.state, dict):
                self.state["error"] = error_message
                self.state["completed"] = True
                self.state["status"] = f"Failed: {error_message}"
                files_found = self.state.get("files_found", 0)
                files_processed = self.state.get("files_processed", 0)
                token_count = len(self.state.get("tokens", []))
            else:
                self.state.error = error_message
                self.state.completed = True
                self.state.status = f"Failed: {error_message}"
                files_found = self.state.files_found
                files_processed = self.state.files_processed
                token_count = len(self.state.tokens)

            return ChatResult(
                success=False,
                files_found=files_found,
                files_processed=files_processed,
                token_count=token_count,
                model="",
                error=error_message,
            )
