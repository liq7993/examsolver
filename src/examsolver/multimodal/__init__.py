"""Multimodal adapters and shared exceptions."""

from __future__ import annotations


class OCRError(Exception):
    """Raised when OCR cannot complete for an input image."""


__all__ = ["OCRError"]

