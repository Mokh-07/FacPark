"""
FacPark - Vision Module (OCR)
Handles license plate character recognition using LPRNet.
Architecture matches SmartALPR_PRO_v2_0_FINAL.ipynb training notebook exactly.
"""

import json
import logging
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# LPRNet ARCHITECTURE - EXACT MATCH WITH TRAINING NOTEBOOK
# =============================================================================
class SmallBasicBlock(nn.Module):
    """Small basic block with BatchNorm - matches training architecture."""
    def __init__(self, in_ch, out_ch, ks):
        super().__init__()
        self.conv = nn.Conv2d(in_ch, out_ch, ks, padding=ks//2, bias=False)
        self.bn = nn.BatchNorm2d(out_ch)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class LPRNet(nn.Module):
    """LPRNet architecture - EXACT match with training notebook."""
    def __init__(self, num_classes, dropout=0.5):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(1, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
            SmallBasicBlock(64, 128, 3), nn.MaxPool2d(3, stride=2, padding=1),
            SmallBasicBlock(128, 256, 3), SmallBasicBlock(256, 256, 3),
            nn.MaxPool2d((2, 1), stride=(2, 1)),
            SmallBasicBlock(256, 256, 3), nn.Dropout(dropout),
            nn.MaxPool2d((2, 1), stride=(2, 1)),
            nn.Conv2d(256, 256, (2, 1)), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
        )
        self.classifier = nn.Sequential(nn.Dropout(dropout), nn.Conv2d(256, num_classes, 1))

    def forward(self, x):
        x = self.backbone(x)
        x = self.classifier(x)
        return F.log_softmax(x.squeeze(2).permute(2, 0, 1), dim=2)


# =============================================================================
# CTC LABEL CONVERTER
# =============================================================================
class CTCLabelConverter:
    """CTC decoder matching training notebook."""
    def __init__(self, characters: str):
        self.BLANK = 0
        self.characters = ['[BLANK]'] + list(characters)
        self.idx_to_char = {i: c for i, c in enumerate(self.characters)}
        self.num_classes = len(self.characters)

    def decode(self, indices):
        result, prev = [], None
        for idx in indices:
            if idx != prev and idx != self.BLANK:
                result.append(self.idx_to_char.get(idx, ''))
            prev = idx
        return ''.join(result)


# =============================================================================
# ARABIC RTL CORRECTION
# =============================================================================
def fix_arabic_rtl(text: str) -> str:
    """
    Inverse les séquences de caractères arabes (RTL correction).
    L'OCR lit gauche→droite, l'arabe s'écrit droite→gauche.
    Exemples:
        "7413 سرنوت 176"  →  "7413 تونس 176"
        "271690 تن"       →  "271690 نت"
    """
    if not text:
        return text
    
    def is_arabic(c):
        return '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F'
    
    result = []
    arabic_buffer = []
    
    for char in text:
        if is_arabic(char):
            arabic_buffer.append(char)
        else:
            if arabic_buffer:
                result.extend(reversed(arabic_buffer))
                arabic_buffer = []
            result.append(char)
    
    if arabic_buffer:
        result.extend(reversed(arabic_buffer))
    
    return ''.join(result)


# =============================================================================
# OCR HANDLER
# =============================================================================
class PlateOCR:
    """LPRNet-based Optical Character Recognition - matches training notebook."""
    
    # Image dimensions matching training config
    OCR_IMG_WIDTH = 128
    OCR_IMG_HEIGHT = 32
    
    def __init__(self):
        self.model_path = settings.OCR_MODEL_PATH
        self.vocab_path = settings.VOCABULARY_PATH
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.converter = None
        self.CHARS = []
        self._load_resources()
    
    def _load_resources(self):
        """Load vocabulary and model."""
        try:
            # 1. Load Vocabulary
            vocab_path = Path(self.vocab_path).resolve()
            if not vocab_path.exists():
                vocab_path = Path("models/vocabulary.json").resolve()
                
            if not vocab_path.exists():
                logger.error(f"Vocabulary not found at {vocab_path}")
                return

            with open(vocab_path, 'r', encoding='utf-8') as f:
                vocab_data = json.load(f)
                # Get characters for CTCLabelConverter
                characters = vocab_data.get('characters', [])
                
                # Handle both list and string formats
                if isinstance(characters, list):
                    # vocabulary.json has characters as a list
                    characters = ''.join(characters)
                elif not characters:
                    # Fallback: build from idx_to_char
                    idx_to_char = vocab_data.get('idx_to_char', {})
                    if isinstance(idx_to_char, dict):
                        sorted_indices = sorted(idx_to_char.keys(), key=lambda x: int(x))
                        characters = ''.join([idx_to_char[k] for k in sorted_indices])
                
                self.converter = CTCLabelConverter(characters)
                self.CHARS = list(characters)
            
            logger.info(f"Loaded {self.converter.num_classes} classes from vocabulary.")

            # 2. Load Model
            model_path = Path(self.model_path).resolve()
            if not model_path.exists():
                model_path = Path("models/SmartALPR_LPRNet_v10_seed456_best.pth").resolve()
                
            if not model_path.exists():
                logger.error(f"OCR model not found at {model_path}")
                return

            # Initialize LPRNet with correct architecture
            self.model = LPRNet(num_classes=self.converter.num_classes, dropout=0.5)
            
            # Load weights
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                val_acc = checkpoint.get('val_acc', 'N/A')
                logger.info(f"Checkpoint val_acc: {val_acc}")
            else:
                state_dict = checkpoint
            
            # Remove module. prefix if present (from DataParallel)
            new_state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
            
            # Load weights strictly - architecture should match exactly now
            self.model.load_state_dict(new_state_dict, strict=True)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("LPRNet OCR model loaded successfully.")
            
        except Exception as e:
            logger.exception(f"Failed to load OCR resources: {e}")

    def transform(self, img):
        """
        Preprocess image for LPRNet - matches training notebook exactly.
        Input: BGR or grayscale image
        Output: normalized tensor ready for model (1, H, W)
        """
        # Convert to Grayscale if needed
        if len(img.shape) == 3 and img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Resize to training dimensions (128x32)
        img = cv2.resize(img, (self.OCR_IMG_WIDTH, self.OCR_IMG_HEIGHT))
        
        # Normalize: (x/255 - 0.5) / 0.5 = x/127.5 - 1
        img = img.astype(np.float32) / 255.0
        img = (img - 0.5) / 0.5
        
        # Add channel dimension -> (1, H, W)
        img = np.expand_dims(img, axis=0)
        
        return img

    def recognize(self, plate_img: np.ndarray) -> str:
        """
        Recognize text from plate image.
        Returns the recognized plate text with Arabic RTL correction applied.
        """
        if self.model is None or self.converter is None:
            self._load_resources()
            if self.model is None:
                return "OCR_ERR"
        
        try:
            # Preprocess image
            img = self.transform(plate_img)
            
            # Create tensor: (1, 1, H, W)
            img_tensor = torch.from_numpy(img).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                # Model output: (seq_len, batch, num_classes) from log_softmax
                preds = self.model(img_tensor)
                
                # Get argmax indices
                _, indices = torch.max(preds, dim=2)
                
                # Decode using CTCLabelConverter
                indices_np = indices.squeeze().cpu().numpy()
                text_raw = self.converter.decode(indices_np)
            
            # Note: LPRNet model outputs text in correct reading order
            # No RTL correction needed - the model was trained this way
            text = text_raw
            
            logger.info(f"OCR result: {text}")
            
            return text
            
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return "OCR_FAIL"
