"""
ONNX Model Inference Engine
Provides fast inference using the exported ONNX model, with fallback to sklearn.
"""

import os
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ONNXInferenceEngine:
    """
    Loads and runs inference against the ONNX-exported crypto model.

    Falls back to the sklearn .pkl model if ONNX runtime is not available
    or the .onnx file is missing.
    """

    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.session = None
        self.input_name: Optional[str] = None
        self.output_name: Optional[str] = None
        self.onnx_available = False
        self.feature_columns = [
            "price_change_1h", "price_change_24h", "volume_change_24h",
            "market_cap_change_24h", "rsi", "macd",
            "moving_avg_7d", "moving_avg_30d",
        ]
        self._load()

    def _load(self):
        """Attempt to load the ONNX model."""
        onnx_path = self.model_dir / "crypto_model.onnx"
        if not onnx_path.exists():
            logger.info("No ONNX model found at %s — ONNX inference disabled", onnx_path)
            return

        try:
            import onnxruntime as ort

            self.session = ort.InferenceSession(
                str(onnx_path),
                providers=["CPUExecutionProvider"],
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.onnx_available = True
            logger.info(
                "ONNX model loaded: input=%s, output=%s",
                self.input_name, self.output_name,
            )
        except ImportError:
            logger.warning("onnxruntime not installed — run: pip install onnxruntime")
        except Exception as e:
            logger.error("Failed to load ONNX model: %s", e)

    def predict(self, features: Dict[str, float]) -> Optional[float]:
        """
        Run inference on a single feature dict.

        Returns the predicted value (next-hour price change) or None on failure.
        """
        if not self.onnx_available or self.session is None:
            return None

        try:
            feature_array = np.array(
                [[features.get(col, 0.0) for col in self.feature_columns]],
                dtype=np.float32,
            )
            result = self.session.run(
                [self.output_name],
                {self.input_name: feature_array},
            )
            prediction = float(result[0][0])
            return prediction
        except Exception as e:
            logger.error("ONNX inference failed: %s", e)
            return None

    def predict_batch(self, features_list: List[Dict[str, float]]) -> List[Optional[float]]:
        """
        Run batch inference on multiple feature dicts.
        """
        if not self.onnx_available or self.session is None:
            return [None] * len(features_list)

        try:
            batch = np.array(
                [[f.get(col, 0.0) for col in self.feature_columns] for f in features_list],
                dtype=np.float32,
            )
            result = self.session.run(
                [self.output_name],
                {self.input_name: batch},
            )
            return [float(v) for v in result[0]]
        except Exception as e:
            logger.error("ONNX batch inference failed: %s", e)
            return [None] * len(features_list)

    def get_status(self) -> Dict[str, Any]:
        """Return ONNX engine status."""
        onnx_path = self.model_dir / "crypto_model.onnx"
        return {
            "onnx_available": self.onnx_available,
            "model_path": str(onnx_path),
            "model_exists": onnx_path.exists(),
            "model_size_bytes": onnx_path.stat().st_size if onnx_path.exists() else 0,
            "input_name": self.input_name,
            "output_name": self.output_name,
            "feature_columns": self.feature_columns,
        }


# ─── Singleton ────────────────────────────────────────────────

_engine: Optional[ONNXInferenceEngine] = None


def get_onnx_engine() -> ONNXInferenceEngine:
    """Get or create the singleton ONNX engine."""
    global _engine
    if _engine is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_dir = os.path.join(project_root, "models")
        _engine = ONNXInferenceEngine(model_dir=model_dir)
    return _engine
