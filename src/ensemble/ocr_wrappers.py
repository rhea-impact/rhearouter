"""
Traditional OCR Wrappers for RheaRouter Ensemble

Provides consistent interface for Tesseract and EasyOCR.
"""

import time
from pathlib import Path
from dataclasses import dataclass
from typing import Union, Optional, List
from PIL import Image
import numpy as np


@dataclass
class TraditionalOCRResult:
    """Result from traditional OCR extraction."""
    text: str
    engine: str
    confidence: float
    time_seconds: float
    success: bool
    boxes: Optional[List[dict]] = None  # Character/word bounding boxes
    error: Optional[str] = None


class TesseractOCR:
    """
    Tesseract OCR wrapper.

    Tesseract excels at clean, high-contrast documents.
    Struggles with blur, noise, and rotation.
    """

    def __init__(self, lang: str = 'eng', config: str = '--oem 3 --psm 6'):
        """
        Initialize Tesseract OCR.

        Args:
            lang: Language code (default 'eng')
            config: Tesseract config string
                    --oem 3: Use LSTM engine
                    --psm 6: Assume uniform block of text
        """
        self.lang = lang
        self.config = config
        self._pytesseract = None

    def _get_tesseract(self):
        """Lazy load pytesseract."""
        if self._pytesseract is None:
            try:
                import pytesseract
                self._pytesseract = pytesseract
            except ImportError:
                raise ImportError(
                    "pytesseract not installed. Run: pip install pytesseract\n"
                    "Also ensure Tesseract is installed: sudo apt install tesseract-ocr"
                )
        return self._pytesseract

    def extract_text(self, image: Union[str, Path, Image.Image, np.ndarray]) -> TraditionalOCRResult:
        """
        Extract text from image using Tesseract.

        Args:
            image: Path to image, PIL Image, or numpy array

        Returns:
            TraditionalOCRResult with extracted text
        """
        pytesseract = self._get_tesseract()
        start_time = time.perf_counter()

        try:
            # Convert to PIL Image if needed
            if isinstance(image, (str, Path)):
                img = Image.open(image)
            elif isinstance(image, np.ndarray):
                img = Image.fromarray(image)
            else:
                img = image

            # Get text with confidence data
            data = pytesseract.image_to_data(img, lang=self.lang, config=self.config, output_type=pytesseract.Output.DICT)

            # Extract text and calculate average confidence
            texts = []
            confidences = []
            boxes = []

            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])

                if text and conf > 0:
                    texts.append(text)
                    confidences.append(conf)
                    boxes.append({
                        'text': text,
                        'confidence': conf / 100.0,
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                    })

            full_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

            elapsed = time.perf_counter() - start_time

            return TraditionalOCRResult(
                text=full_text,
                engine='tesseract',
                confidence=avg_confidence,
                time_seconds=elapsed,
                success=True,
                boxes=boxes
            )

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return TraditionalOCRResult(
                text='',
                engine='tesseract',
                confidence=0.0,
                time_seconds=elapsed,
                success=False,
                error=str(e)
            )

    def __repr__(self):
        return f"TesseractOCR(lang={self.lang})"


class EasyOCRWrapper:
    """
    EasyOCR wrapper.

    EasyOCR uses deep learning and handles varied fonts/styles better.
    More robust to some degradations than Tesseract.
    """

    def __init__(self, lang_list: List[str] = None, gpu: bool = True):
        """
        Initialize EasyOCR.

        Args:
            lang_list: List of language codes (default ['en'])
            gpu: Whether to use GPU acceleration
        """
        self.lang_list = lang_list or ['en']
        self.gpu = gpu
        self._reader = None

    def _get_reader(self):
        """Lazy load EasyOCR reader."""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self.lang_list, gpu=self.gpu)
            except ImportError:
                raise ImportError(
                    "easyocr not installed. Run: pip install easyocr"
                )
        return self._reader

    def extract_text(self, image: Union[str, Path, Image.Image, np.ndarray]) -> TraditionalOCRResult:
        """
        Extract text from image using EasyOCR.

        Args:
            image: Path to image, PIL Image, or numpy array

        Returns:
            TraditionalOCRResult with extracted text
        """
        reader = self._get_reader()
        start_time = time.perf_counter()

        try:
            # Convert to numpy array if needed
            if isinstance(image, Image.Image):
                img_array = np.array(image)
            elif isinstance(image, (str, Path)):
                img_array = np.array(Image.open(image))
            else:
                img_array = image

            # Run OCR
            results = reader.readtext(img_array)

            # Extract text and confidence
            texts = []
            confidences = []
            boxes = []

            for bbox, text, conf in results:
                texts.append(text)
                confidences.append(conf)
                boxes.append({
                    'text': text,
                    'confidence': conf,
                    'bbox': bbox,  # [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                })

            full_text = ' '.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            elapsed = time.perf_counter() - start_time

            return TraditionalOCRResult(
                text=full_text,
                engine='easyocr',
                confidence=avg_confidence,
                time_seconds=elapsed,
                success=True,
                boxes=boxes
            )

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return TraditionalOCRResult(
                text='',
                engine='easyocr',
                confidence=0.0,
                time_seconds=elapsed,
                success=False,
                error=str(e)
            )

    def __repr__(self):
        return f"EasyOCRWrapper(langs={self.lang_list})"


class HybridOCR:
    """
    Combines Tesseract and EasyOCR for better coverage.

    Uses both engines and provides combined results for ensemble voting.
    """

    def __init__(self, use_easyocr: bool = False):
        """
        Initialize HybridOCR.

        Args:
            use_easyocr: Whether to include EasyOCR (requires model download)
        """
        self.tesseract = TesseractOCR()
        self.use_easyocr = use_easyocr
        self._easyocr = None

    @property
    def easyocr(self):
        """Lazy-load EasyOCR only when needed."""
        if self._easyocr is None:
            self._easyocr = EasyOCRWrapper()
        return self._easyocr

    def extract_all(self, image: Union[str, Path, Image.Image, np.ndarray]) -> List[TraditionalOCRResult]:
        """
        Run OCR engines and return all results.

        Returns:
            List of TraditionalOCRResult from each engine
        """
        results = []

        # Run Tesseract
        try:
            results.append(self.tesseract.extract_text(image))
        except Exception as e:
            results.append(TraditionalOCRResult(
                text='', engine='tesseract', confidence=0.0,
                time_seconds=0.0, success=False, error=str(e)
            ))

        # Run EasyOCR only if enabled
        if self.use_easyocr:
            try:
                results.append(self.easyocr.extract_text(image))
            except Exception as e:
                results.append(TraditionalOCRResult(
                    text='', engine='easyocr', confidence=0.0,
                    time_seconds=0.0, success=False, error=str(e)
                ))

        return results
