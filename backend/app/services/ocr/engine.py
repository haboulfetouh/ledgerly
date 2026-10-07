"""Local OCR engine abstraction.

Tesseract is the MVP implementation — small Docker image, no GPU, fast to
get the pipeline running end-to-end. It sits behind this interface so it
can be swapped for a layout-aware engine (PaddleOCR, docTR) later without
touching the extraction/matching business logic, if real-world scanned
invoice accuracy turns out to need it.
"""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from dataclasses import dataclass

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


@dataclass
class OcrResult:
    text: str
    mean_confidence: float | None  # 0-100, None if the engine can't report one
    page_count: int


class OcrEngine(ABC):
    @abstractmethod
    def extract_text(self, file_bytes: bytes, content_type: str) -> OcrResult: ...


class TesseractOcrEngine(OcrEngine):
    _PDF_RENDER_DPI = 200

    def extract_text(self, file_bytes: bytes, content_type: str) -> OcrResult:
        images = self._to_images(file_bytes, content_type)

        texts: list[str] = []
        confidences: list[float] = []

        for image in images:
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )
            page_text = " ".join(t for t in data["text"] if t.strip())
            texts.append(page_text)

            page_confidences = [float(c) for c in data["conf"] if c not in ("-1", -1)]
            if page_confidences:
                confidences.append(sum(page_confidences) / len(page_confidences))

        mean_confidence = sum(confidences) / len(confidences) if confidences else None

        return OcrResult(
            text="\n\n".join(texts),
            mean_confidence=mean_confidence,
            page_count=len(images),
        )

    def _to_images(self, file_bytes: bytes, content_type: str) -> list[Image.Image]:
        if content_type == "application/pdf":
            images = []
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            zoom = self._PDF_RENDER_DPI / 72
            matrix = fitz.Matrix(zoom, zoom)
            for page in doc:
                pixmap = page.get_pixmap(matrix=matrix)
                images.append(Image.open(io.BytesIO(pixmap.tobytes("png"))))
            doc.close()
            return images

        return [Image.open(io.BytesIO(file_bytes))]


def get_ocr_engine() -> OcrEngine:
    return TesseractOcrEngine()
