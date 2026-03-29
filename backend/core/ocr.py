"""
SmartOCR — Industry-Level Tesseract OCR System
================================================
Single file. No PaddleOCR. No server. Just run it.

Usage:
  python ocr.py                          (uses DEFAULT_IMAGE below)
  python ocr.py test.jpg
  python ocr.py test.jpg --psm 6
  python ocr.py test.jpg --debug        (also saves preprocessed image)
"""

import sys
import cv2
import json
import time
import logging
import argparse
import numpy as np
import pytesseract
from PIL import Image
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from collections import defaultdict

# ══════════════════════════════════════════════════════════
# CONFIG  ← edit these
# ══════════════════════════════════════════════════════════

DEFAULT_IMAGE = r"C:\Users\abhij\OneDrive\Desktop\project mamaji\search engine\test.jpg"

# Windows path to tesseract.exe — leave None on Linux/Mac
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TESSERACT_LANG       = "eng"
CONFIDENCE_THRESHOLD = 40      # drop words below this % (0–100)
UPSCALE_FACTOR       = 2.0
OEM                  = 3       # 3 = LSTM only (best)

# ══════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("SmartOCR")

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


# ══════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════

class ImageType(Enum):
    CLEAN_DOCUMENT = "clean_document"
    TABLE          = "table"
    SPARSE_TEXT    = "sparse_text"
    LOW_QUALITY    = "low_quality"
    HANDWRITTEN    = "handwritten"
    UNKNOWN        = "unknown"


PSM_MAP = {
    ImageType.CLEAN_DOCUMENT: 6,
    ImageType.TABLE:          6,
    ImageType.SPARSE_TEXT:    11,
    ImageType.LOW_QUALITY:    6,
    ImageType.HANDWRITTEN:    6,
    ImageType.UNKNOWN:        3,
}


# ══════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════

@dataclass
class Word:
    text:       str
    confidence: float
    bbox:       list
    line_num:   int
    block_num:  int


@dataclass
class OCRResult:
    words:              list
    lines:              list
    full_text:          str
    image_type:         ImageType
    psm_used:           int
    avg_confidence:     float
    word_count:         int
    processing_time_ms: float
    image_path:         str
    image_shape:        list

    def display(self):
        W   = 62
        bar = "=" * W

        def row(label, value):
            print(f"  {label:<22} {value}")

        print(f"\n+{bar}+")
        print(f"|{'  SmartOCR Result':^{W+2}}|")
        print(f"+{bar}+")
        row("File",           Path(self.image_path).name)
        row("Image Type",     self.image_type.value)
        row("PSM Used",       str(self.psm_used))
        row("Avg Confidence", f"{self.avg_confidence:.1%}")
        row("Words Found",    str(self.word_count))
        row("Time",           f"{self.processing_time_ms:.0f} ms")
        print(f"+{bar}+")
        print(f"|{'  Extracted Text':^{W+2}}|")
        print(f"+{bar}+")
        if self.lines:
            for line in self.lines:
                while len(line) > W - 2:
                    print(f"  {line[:W-2]}")
                    line = line[W-2:]
                if line.strip():
                    print(f"  {line}")
        else:
            print("  (no text detected)")
        print(f"+{bar}+\n")

    def to_dict(self):
        return {
            "full_text":          self.full_text,
            "lines":              self.lines,
            "image_type":         self.image_type.value,
            "psm_used":           self.psm_used,
            "avg_confidence":     round(self.avg_confidence, 4),
            "word_count":         self.word_count,
            "processing_time_ms": round(self.processing_time_ms, 1),
            "image_path":         self.image_path,
            "image_shape":        self.image_shape,
            "words": [
                {
                    "text":       w.text,
                    "confidence": round(w.confidence, 4),
                    "bbox":       w.bbox,
                    "line_num":   w.line_num,
                    "block_num":  w.block_num,
                }
                for w in self.words
            ],
        }


# ══════════════════════════════════════════════════════════
# IMAGE CLASSIFIER  (fixed)
# ══════════════════════════════════════════════════════════

class ImageClassifier:

    def classify(self, img: np.ndarray) -> ImageType:
        gray = self._gray(img)

        sharpness    = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        noise        = float(np.std(gray))
        contrast     = float(gray.max()) - float(gray.min())
        line_density = self._line_density(gray)
        dark_ratio   = float(np.mean(gray < 50))
        light_ratio  = float(np.mean(gray > 200))

        # FIX: measure uniformity of DARK pixels (ink), not bright background.
        # For a pure white-bg doc, std of bright pixels is ~0 (all 255) which
        # previously made bg_uniformity=0 and caused wrong classification.
        ink_std = self._ink_std(gray)

        log.info(
            f"Classify → sharpness={sharpness:.0f}  noise={noise:.1f}  "
            f"contrast={contrast:.0f}  lines={line_density:.3f}  "
            f"dark={dark_ratio:.2f}  light={light_ratio:.2f}  "
            f"ink_std={ink_std:.1f}"
        )

        # ── Very blurry + low noise → degraded scan ──────────────
        if sharpness < 40 and noise < 18:
            return ImageType.LOW_QUALITY

        # ── Bright background + high contrast + sharp ─────────────
        # This is the clean document / table zone.
        if light_ratio > 0.55 and contrast > 150 and sharpness > 100:
            # Tables have dense crossing lines; documents don't
            if line_density > 0.20:
                return ImageType.TABLE
            return ImageType.CLEAN_DOCUMENT

        # ── High contrast + moderate line structure ────────────────
        if contrast > 160 and line_density > 0.08:
            if line_density > 0.20:
                return ImageType.TABLE
            return ImageType.CLEAN_DOCUMENT

        # ── Sharp + mostly white + low ink → handwriting ──────────
        if sharpness > 150 and light_ratio > 0.40 and dark_ratio < 0.10:
            return ImageType.HANDWRITTEN

        # ── Very sparse ink → receipt / sign / label ──────────────
        if dark_ratio < 0.04 and contrast > 120:
            return ImageType.SPARSE_TEXT

        return ImageType.UNKNOWN

    @staticmethod
    def _gray(img: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    @staticmethod
    def _line_density(gray: np.ndarray) -> float:
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                threshold=80, minLineLength=60, maxLineGap=10)
        if lines is None:
            return 0.0
        h, w = gray.shape
        return len(lines) / max(1.0, h * w / 10_000)

    @staticmethod
    def _ink_std(gray: np.ndarray) -> float:
        """Std-dev of dark pixels (the ink). More reliable than background std."""
        flat = gray.flatten()
        ink  = flat[flat < np.percentile(flat, 30)]   # darkest 30%
        return float(np.std(ink)) if len(ink) else 0.0


# ══════════════════════════════════════════════════════════
# PREPROCESSOR
# ══════════════════════════════════════════════════════════

class Preprocessor:

    def process(self, img: np.ndarray, image_type: ImageType) -> np.ndarray:
        pipelines = {
            ImageType.CLEAN_DOCUMENT: self._clean_document,
            ImageType.TABLE:          self._table,
            ImageType.SPARSE_TEXT:    self._sparse_text,
            ImageType.LOW_QUALITY:    self._low_quality,
            ImageType.HANDWRITTEN:    self._handwritten,
            ImageType.UNKNOWN:        self._generic,
        }
        fn = pipelines.get(image_type, self._generic)
        log.info(f"Pipeline → {fn.__name__}")
        return fn(img)

    # ── pipelines ─────────────────────────────────────────

    def _clean_document(self, img):
        g = self._gray(img)
        g = self._upscale(g)
        # FIX: only deskew if truly needed; skip for already-straight docs
        g = self._safe_deskew(g)
        g = self._remove_shadow(g)
        g = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 31, 11)
        g = cv2.fastNlMeansDenoising(g, h=10)
        g = self._morph_close(g)
        return g

    def _table(self, img):
        g = self._gray(img)
        g = self._upscale(g)
        g = self._safe_deskew(g)
        _, g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        g = cv2.fastNlMeansDenoising(g, h=8)
        return g

    def _sparse_text(self, img):
        g = self._gray(img)
        g = self._upscale(g, factor=1.5)
        g = self._safe_deskew(g)
        g = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY, 21, 8)
        return g

    def _low_quality(self, img):
        g = self._gray(img)
        kernel = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
        g = cv2.filter2D(g, -1, kernel)
        g = self._upscale(g, factor=3.0)
        g = cv2.bilateralFilter(g, 11, 80, 80)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        g = clahe.apply(g)
        g = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 41, 15)
        g = cv2.fastNlMeansDenoising(g, h=15)
        return g

    def _handwritten(self, img):
        g = self._gray(img)
        g = self._upscale(g)
        g = self._remove_shadow(g)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        g = clahe.apply(g)
        g = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 25, 10)
        g = cv2.fastNlMeansDenoising(g, h=12)
        return g

    def _generic(self, img):
        g = self._gray(img)
        g = self._upscale(g)
        g = self._safe_deskew(g)
        g = cv2.bilateralFilter(g, 9, 75, 75)
        g = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, 31, 11)
        g = cv2.fastNlMeansDenoising(g, h=10)
        return g

    # ── shared utilities ──────────────────────────────────

    @staticmethod
    def _gray(img):
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

    @staticmethod
    def _upscale(img, factor=UPSCALE_FACTOR):
        return cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def _remove_shadow(gray):
        dilated = cv2.dilate(gray, np.ones((7, 7), np.uint8))
        bg      = cv2.medianBlur(dilated, 21)
        diff    = cv2.absdiff(gray, bg)
        norm    = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        _, out  = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return out

    @staticmethod
    def _safe_deskew(gray):
        """
        FIX: Deskew only for small angles (±10°).
        The old version computed a -90° rotation for straight images because
        minAreaRect on a nearly-axis-aligned text block returns the angle of
        the SHORT side, which can be ~90° away from intuition.
        We now clamp to ±10° so perfectly straight images are left untouched.
        """
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 10:
            return gray

        angle = cv2.minAreaRect(coords)[-1]

        # Normalise to (-45, 45] range
        if angle < -45:
            angle = 90 + angle

        # SAFETY CLAMP: only correct small real-world skew; ignore large angles
        # that are artifacts of minAreaRect on tall/wide bounding boxes
        if abs(angle) < 0.5 or abs(angle) > 10:
            return gray

        log.info(f"Deskewing {angle:.2f}°")
        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    @staticmethod
    def _morph_close(gray, ksize=1):
        if ksize < 1:
            return gray
        kernel = np.ones((ksize, ksize), np.uint8)
        return cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)


# ══════════════════════════════════════════════════════════
# TESSERACT RUNNER
# ══════════════════════════════════════════════════════════

class TesseractRunner:

    def run(self, img: np.ndarray, psm: int) -> list:
        config = f"--oem {OEM} --psm {psm}"
        pil    = Image.fromarray(img)

        data = pytesseract.image_to_data(
            pil,
            lang=TESSERACT_LANG,
            config=config,
            output_type=pytesseract.Output.DICT,
        )

        words = []
        scale = 1.0 / UPSCALE_FACTOR

        for i in range(len(data["text"])):
            raw  = str(data["text"][i]).strip()
            conf = float(data["conf"][i])

            if not raw or conf < CONFIDENCE_THRESHOLD:
                continue

            x1 = int(data["left"][i] * scale)
            y1 = int(data["top"][i]  * scale)
            x2 = int((data["left"][i] + data["width"][i])  * scale)
            y2 = int((data["top"][i]  + data["height"][i]) * scale)

            words.append(Word(
                text      = raw,
                confidence= conf / 100.0,
                bbox      = [x1, y1, x2, y2],
                line_num  = int(data["line_num"][i]),
                block_num = int(data["block_num"][i]),
            ))

        return words

    @staticmethod
    def words_to_lines(words: list) -> list:
        buckets = defaultdict(list)
        for w in words:
            buckets[(w.block_num, w.line_num)].append(w)

        lines = []
        for key in sorted(buckets):
            sorted_words = sorted(buckets[key], key=lambda w: w.bbox[0])
            line_str     = " ".join(w.text for w in sorted_words)
            if line_str.strip():
                lines.append(line_str)

        return lines


# ══════════════════════════════════════════════════════════
# SMART OCR — ORCHESTRATOR
# ══════════════════════════════════════════════════════════

class SmartOCR:

    def __init__(self):
        self.classifier   = ImageClassifier()
        self.preprocessor = Preprocessor()
        self.runner       = TesseractRunner()

    def process(self, image_path: str, force_psm: int = None, debug: bool = False) -> OCRResult:
        t0 = time.perf_counter()

        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        original_shape = list(img.shape)
        log.info(f"Loaded  {Path(image_path).name}  {original_shape[1]}x{original_shape[0]}")

        image_type = self.classifier.classify(img)
        log.info(f"Image type: [{image_type.value}]")

        psm = force_psm if force_psm is not None else PSM_MAP[image_type]
        log.info(f"PSM={psm}  OEM={OEM}")

        processed = self.preprocessor.process(img, image_type)

        if debug:
            debug_path = str(Path(image_path).with_suffix("")) + "_preprocessed.png"
            cv2.imwrite(debug_path, processed)
            log.info(f"Debug image saved → {debug_path}")

        words = self.runner.run(processed, psm)
        log.info(f"Words extracted: {len(words)}  (threshold={CONFIDENCE_THRESHOLD}%)")

        lines     = self.runner.words_to_lines(words)
        full_text = "\n".join(lines)
        avg_conf  = (sum(w.confidence for w in words) / len(words)) if words else 0.0
        elapsed   = (time.perf_counter() - t0) * 1000

        return OCRResult(
            words              = words,
            lines              = lines,
            full_text          = full_text,
            image_type         = image_type,
            psm_used           = psm,
            avg_confidence     = avg_conf,
            word_count         = len(words),
            processing_time_ms = elapsed,
            image_path         = str(Path(image_path).resolve()),
            image_shape        = original_shape,
        )


# ══════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="SmartOCR — Industry-level Tesseract OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PSM reference:
  3  = Fully automatic (default for unknown images)
  6  = Single uniform block of text
  11 = Sparse text (receipts, signs)

Examples:
  python ocr.py
  python ocr.py test.jpg
  python ocr.py test.jpg --psm 6
  python ocr.py test.jpg --debug
        """,
    )
    p.add_argument("image", nargs="?", default=DEFAULT_IMAGE,
                   help="Path to image (default: DEFAULT_IMAGE in config)")
    p.add_argument("--psm",   type=int, default=None,
                   help="Force Tesseract PSM 0–13 (default: auto)")
    p.add_argument("--debug", action="store_true",
                   help="Save preprocessed image for inspection")
    return p.parse_args()


def main():
    args = parse_args()

    if not Path(args.image).exists():
        print(f"\n  ERROR: Image not found: {args.image}")
        print(f"  Edit DEFAULT_IMAGE at the top of ocr.py or pass the path as an argument.\n")
        sys.exit(1)

    ocr    = SmartOCR()
    result = ocr.process(args.image, force_psm=args.psm, debug=args.debug)

    result.display()

    out_json = str(Path(args.image).with_suffix("")) + "_ocr.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    log.info(f"JSON saved → {out_json}")


if __name__ == "__main__":
    main()