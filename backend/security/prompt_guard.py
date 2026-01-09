"""
Prompt injection detection and prevention.

Protects against:
- Instruction override attempts
- System prompt leakage
- Jailbreak patterns
- Role confusion attacks
"""

import re


class PromptInjectionError(Exception):
    """Raised when prompt injection is detected."""

    pass


class PromptGuard:
    """Detects and prevents prompt injection attacks."""

    # Patterns that indicate injection attempts
    DANGEROUS_PATTERNS = [
        # Direct instruction override
        (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", "instruction override"),
        (r"disregard\s+(all\s+)?(previous|prior|above)", "instruction override"),
        (r"forget\s+(all\s+)?(previous|prior|above)", "instruction override"),
        # System prompt manipulation
        (r"system\s*:", "system prompt injection"),
        (r"<\|im_start\|>", "chat template injection"),
        (r"<\|im_end\|>", "chat template injection"),
        (r"###\s*system", "system delimiter injection"),
        # Role confusion
        (r"you\s+are\s+now", "role confusion"),
        (r"act\s+as\s+(if\s+)?you\s+(are|were)", "role confusion"),
        (r"pretend\s+you\s+are", "role confusion"),
        # Jailbreak attempts
        (r"developer\s+mode", "jailbreak attempt"),
        (r"DAN\s+mode", "jailbreak attempt (DAN)"),
        (r"sudo\s+mode", "jailbreak attempt"),
        # Prompt leakage
        (r"print\s+your\s+(system\s+)?(prompt|instructions)", "prompt leakage"),
        (r"show\s+me\s+your\s+(system\s+)?(prompt|instructions)", "prompt leakage"),
        (r"what\s+(are|were)\s+your\s+(original\s+)?(instructions|rules)", "prompt leakage"),
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize prompt guard.

        Args:
            strict_mode: If True, reject on any suspicious pattern.
                        If False, only reject high-confidence injections.
        """
        self.strict_mode = strict_mode
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc) for pattern, desc in self.DANGEROUS_PATTERNS
        ]

    def scan(self, user_input: str) -> list[tuple[str, str]]:
        """
        Scan input for injection patterns.

        Args:
            user_input: User-provided text to scan

        Returns:
            List of (pattern_match, description) tuples
        """
        if not user_input or not user_input.strip():
            return []

        detections = []

        for pattern, description in self.compiled_patterns:
            match = pattern.search(user_input)
            if match:
                detections.append((match.group(0), description))

        return detections

    def validate(self, user_input: str) -> str:
        """
        Validate user input and raise if injection detected.

        Args:
            user_input: User-provided text

        Returns:
            Original input if safe

        Raises:
            PromptInjectionError: If injection detected
        """
        detections = self.scan(user_input)

        if detections:
            patterns_found = ", ".join(f"'{match}' ({desc})" for match, desc in detections)
            raise PromptInjectionError(f"Potential prompt injection detected: {patterns_found}")

        return user_input

    def sanitize(self, user_input: str) -> str:
        """
        Sanitize input by escaping special characters.

        Args:
            user_input: User-provided text

        Returns:
            Escaped text safe for inclusion in prompts
        """
        if not user_input:
            return ""

        # Escape XML-like tags used in Claude prompt structure
        sanitized = user_input.replace("<", "&lt;").replace(">", "&gt;")

        # Escape backticks to prevent markdown code block injection
        sanitized = sanitized.replace("`", "\\`")

        return sanitized

    def build_safe_prompt(
        self,
        user_query: str,
        documents: list[str],
        system_instruction: str = "You are a helpful document analysis assistant.",
    ) -> str:
        """
        Build structured prompt with clear boundaries.

        Args:
            user_query: Validated and sanitized user query
            documents: List of document contents
            system_instruction: System-level instruction

        Returns:
            Structured prompt with injection resistance
        """
        self.validate(user_query)

        safe_query = self.sanitize(user_query)
        safe_docs = [self.sanitize(doc) for doc in documents]

        prompt = f"""{system_instruction}

<documents>
{chr(10).join(f"<document>{doc}</document>" for doc in safe_docs)}
</documents>

<user_query>
{safe_query}
</user_query>

Please analyze the documents above and answer the user's query. Base your response only on the provided documents."""

        return prompt
