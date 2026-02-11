"""
FacPark - Vision API
License plate detection and recognition endpoints.
Uses YOLO for detection and LPRNet for OCR.
"""

import io
import base64
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.session import get_db
from backend.db.models import User
from backend.api.auth import get_current_user, get_current_admin
from backend.core.decision import check_plate_access

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================
class PlateDetection(BaseModel):
    plate: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]


class DetectionResponse(BaseModel):
    success: bool
    plates: List[PlateDetection]
    image_base64: Optional[str] = None  # Annotated image
    message: str


class AccessCheckRequest(BaseModel):
    plate: str


class AccessCheckResponse(BaseModel):
    decision: str
    ref_code: str
    message: str
    user_id: Optional[int] = None
    slot_code: Optional[str] = None
    subscription_type: Optional[str] = None
    expires_at: Optional[str] = None


# =============================================================================
# LAZY LOAD VISION MODELS
# =============================================================================
_detector = None
_ocr = None


def get_detector():
    """Lazy load YOLO detector."""
    global _detector
    if _detector is None:
        from backend.vision.detector import PlateDetector
        _detector = PlateDetector()
    return _detector


def get_ocr():
    """Lazy load OCR model."""
    global _ocr
    if _ocr is None:
        from backend.vision.ocr import PlateOCR
        _ocr = PlateOCR()
    return _ocr


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.post("/detect", response_model=DetectionResponse)
async def detect_plates(
    file: UploadFile = File(...),
    annotate: bool = True,
    current_user: User = Depends(get_current_user)
):
    """
    Detect license plates in an uploaded image.
    
    Returns detected plates with confidence and bounding boxes.
    Optionally returns annotated image as base64.
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit être une image (JPEG, PNG)"
        )
    
    try:
        # Read image
        image_bytes = await file.read()
        
        # Detect plates
        detector = get_detector()
        detections = detector.detect(image_bytes)
        
        if not detections:
            return DetectionResponse(
                success=True,
                plates=[],
                message="Aucune plaque détectée dans l'image."
            )
        
        # OCR on each detection
        ocr = get_ocr()
        plates = []
        
        for det in detections:
            # Crop plate region
            plate_img = detector.crop_plate(image_bytes, det["bbox"])
            
            # Recognize text
            plate_text = ocr.recognize(plate_img)
            
            plates.append(PlateDetection(
                plate=plate_text,
                confidence=det["confidence"],
                bbox=det["bbox"]
            ))
        
        # Annotate image if requested
        annotated_b64 = None
        if annotate:
            annotated_img = detector.annotate(image_bytes, detections, plates)
            annotated_b64 = base64.b64encode(annotated_img).decode("utf-8")
        
        return DetectionResponse(
            success=True,
            plates=plates,
            image_base64=annotated_b64,
            message=f"{len(plates)} plaque(s) détectée(s)."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la détection: {str(e)}"
        )


@router.post("/check-access", response_model=AccessCheckResponse)
async def check_access(
    request_data: AccessCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Check if a plate is allowed access.
    
    Uses the Decision Engine (the ONLY authority for access decisions).
    Admin only endpoint.
    """
    client_ip = request.client.host if request.client else None
    
    result = check_plate_access(
        db=db,
        plate=request_data.plate,
        checked_by=current_user.id,
        ip_address=client_ip
    )
    
    return AccessCheckResponse(
        decision=result.decision.value,
        ref_code=result.ref_code,
        message=result.message,
        user_id=result.user_id,
        slot_code=result.slot_code,
        subscription_type=result.subscription_type,
        expires_at=result.expires_at.isoformat() if result.expires_at else None
    )


@router.post("/detect-and-check", response_model=dict)
async def detect_and_check_access(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Combined endpoint: Detect plate from image and check access.
    
    Admin only. This is what the parking gate would call.
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit être une image"
        )
    
    try:
        # Read image
        image_bytes = await file.read()
        
        # Detect plates
        detector = get_detector()
        detections = detector.detect(image_bytes)
        
        if not detections:
            return {
                "success": False,
                "detection": None,
                "access": {
                    "decision": "DENY",
                    "ref_code": settings.REF_CODES["PLATE_NOT_FOUND"],
                    "message": "Aucune plaque détectée. Approchez du capteur."
                }
            }
        
        # Use first detected plate (highest confidence)
        best_detection = max(detections, key=lambda x: x["confidence"])
        
        # OCR
        ocr = get_ocr()
        plate_img = detector.crop_plate(image_bytes, best_detection["bbox"])
        plate_text = ocr.recognize(plate_img)
        
        # Check access
        client_ip = request.client.host if request.client else None
        access_result = check_plate_access(
            db=db,
            plate=plate_text,
            checked_by=current_user.id,
            ip_address=client_ip
        )
        
        return {
            "success": True,
            "detection": {
                "plate": plate_text,
                "confidence": best_detection["confidence"]
            },
            "access": {
                "decision": access_result.decision.value,
                "ref_code": access_result.ref_code,
                "message": access_result.message,
                "slot_code": access_result.slot_code
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )
