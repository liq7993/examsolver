"""Multimodal adapters and shared exceptions."""

from __future__ import annotations


class OCRError(Exception):
    """Raised when OCR cannot complete for an input image."""


class VLMError(Exception):
    """Raised when cloud vision description cannot complete."""


__all__ = ["OCRError", "VLMError"]
