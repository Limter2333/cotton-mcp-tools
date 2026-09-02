"""Abstract base class for multimodal services."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MultimodalService(ABC):
    """Abstract base class for multimodal API services.

    All multimodal service implementations must inherit from this class
    and implement the analyze_image method.
    """

    @abstractmethod
    async def analyze_image(
        self,
        image: str,
        prompt: str,
        model: str | None = None,
    ) -> str:
        """Analyze an image with a text prompt.

        Args:
            image: Base64-encoded image data or HTTP(S) URL.
            prompt: Text prompt describing the analysis task.
            model: Optional model override. Uses service default if None.

        Returns:
            The model's text response.

        Raises:
            ValueError: If the image format is invalid.
            RuntimeError: If the API call fails.
        """
        ...
