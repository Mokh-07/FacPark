"""
FacPark - Vision Module (YOLO)
Handles license plate detection using YOLOv11 model.
"""

import numpy as np
import cv2
import logging
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
from pathlib import Path
from typing import List, Dict, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class PlateDetector:
    """YOLO-based License Plate Detector."""
    
    def __init__(self):
        self.model_path = settings.YOLO_MODEL_PATH
        self.conf_threshold = settings.YOLO_CONFIDENCE
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model."""
        if not self.model:
            try:
                # Resolve true path via pathlib
                path = Path(self.model_path).resolve()
                if not path.exists():
                     # Fallback to direct path if config resolution failed
                    path = Path("models/smartalpr_hybrid_640_yolo11l_v2_best.pt").resolve()
                
                if not path.exists():
                    logger.error(f"YOLO model not found at {path}")
                    return

                logger.info(f"Loading YOLO model from {path}...")
                self.model = YOLO(str(path))
                logger.info("YOLO model loaded successfully.")
            except Exception as e:
                logger.exception(f"Failed to load YOLO model: {e}")
    
    def detect(self, image_bytes: bytes) -> List[Dict]:
        """
        Detect plates in an image byte stream.
        Returns list of detections: {"bbox": [x1, y1, x2, y2], "confidence": float}
        """
        if not self.model:
            self._load_model()
            if not self.model:
                return []
        
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Run inference
            results = self.model.predict(
                source=img,
                conf=self.conf_threshold,
                verbose=False
            )
            
            detections = []
            result = results[0]
            
            if result.boxes:
                for box in result.boxes:
                    coords = box.xyxy[0].tolist()  # x1, y1, x2, y2
                    conf = float(box.conf[0])
                    
                    # Ensure coordinates are within image bounds
                    h, w, _ = img.shape
                    x1, y1, x2, y2 = coords
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(w, x2)
                    y2 = min(h, y2)
                    
                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": conf,
                        "class": int(box.cls[0])
                    })
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []

    def crop_plate(self, image_bytes: bytes, bbox: List[float]) -> Optional[np.ndarray]:
        """Crop plate region from image based on bbox."""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            x1, y1, x2, y2 = map(int, bbox)
            
            # Crop
            plate_img = img[y1:y2, x1:x2]
            return plate_img
            
        except Exception as e:
            logger.error(f"Crop error: {e}")
            return None

    def annotate(self, image_bytes: bytes, detections: List[Dict], plates_info: List[Dict] = None) -> bytes:
        """Annotate image with bounding boxes and recognized text."""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to PIL for better text drawing (optional, but using cv2 for speed here)
            for i, det in enumerate(detections):
                x1, y1, x2, y2 = map(int, det["bbox"])
                conf = det["confidence"]
                
                # Draw box
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                label = f"Plate: {conf:.2f}"
                if plates_info and i < len(plates_info):
                    label = f"{plates_info[i].plate} ({conf:.2f})"
                
                # Background for text
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                cv2.rectangle(img, (x1, y1 - 25), (x1 + w, y1), (0, 255, 0), -1)
                cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            
            # Encode back to bytes
            _, encoded_img = cv2.imencode('.jpg', img)
            return encoded_img.tobytes()
            
        except Exception as e:
            logger.error(f"Annotation error: {e}")
            return image_bytes
