"""
FacPark - Chat API
Chat endpoint with LLM + RAG integration.
Tools are called based on user role.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.session import get_db
from backend.db.models import User, UserRole
from backend.api.auth import get_current_user
from backend.core.agent import process_message
from backend.core.tools import (
    get_my_profile, get_my_vehicles, get_my_subscription,
    get_my_slot, get_my_access_history, get_my_suspension_status, ask_reglement
)
from backend.core.tools_admin import (
    list_students, create_student, delete_student,
    add_vehicle, remove_vehicle, create_subscription,
    renew_subscription, assign_slot, suspend_access,
    get_admin_stats, admin_check_plate_access
)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================
class ChatMessage(BaseModel):
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {"message": "Combien de véhicules puis-je enregistrer?"}
        }


class ChatResponse(BaseModel):
    response: str
    citations: List[dict] = []
    rag_used: bool = False
    model: Optional[str] = None
    blocked: bool = False


class ToolCall(BaseModel):
    tool_name: str
    params: dict = {}
    
    class Config:
        json_schema_extra = {
            "example": {"tool_name": "get_my_vehicles", "params": {}}
        }


# =============================================================================
# TOOL REGISTRY
# =============================================================================
STUDENT_TOOLS = {
    "get_my_profile": get_my_profile,
    "get_my_vehicles": get_my_vehicles,
    "get_my_subscription": get_my_subscription,
    "get_my_slot": get_my_slot,
    "get_my_access_history": get_my_access_history,
    "get_my_suspension_status": get_my_suspension_status,
    "ask_reglement": ask_reglement,
}

ADMIN_TOOLS = {
    "list_students": list_students,
    "create_student": create_student,
    "delete_student": delete_student,
    "add_vehicle": add_vehicle,
    "remove_vehicle": remove_vehicle,
    "create_subscription": create_subscription,
    "renew_subscription": renew_subscription,
    "assign_slot": assign_slot,
    "suspend_access": suspend_access,
    "get_admin_stats": get_admin_stats,
    "check_plate_access": admin_check_plate_access,
}


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.post("/message", response_model=ChatResponse)
async def send_message(
    chat: ChatMessage,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a chat message to the AI assistant.
    
    The assistant:
    - Answers questions about the parking regulations (using RAG)
    - Can call tools to get/modify data based on user role
    - Never makes access decisions (only Decision Engine does)
    """
    client_ip = request.client.host if request.client else None
    
    result = await process_message(
        db=db,
        user=current_user,
        message=chat.message,
        ip=client_ip
    )
    
    return ChatResponse(
        response=result.get("response", ""),
        citations=result.get("citations", []),
        rag_used=result.get("rag_used", False),
        model=result.get("model"),
        blocked=result.get("blocked", False)
    )


@router.post("/tool")
async def call_tool(
    tool_call: ToolCall,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Directly call a tool.
    
    Student tools: get_my_profile, get_my_vehicles, get_my_subscription,
                   get_my_slot, get_my_access_history, ask_reglement
    
    Admin tools: list_students, create_student, delete_student, add_vehicle,
                 remove_vehicle, create_subscription, renew_subscription,
                 assign_slot, suspend_access, get_admin_stats, check_plate_access
    """
    tool_name = tool_call.tool_name
    params = tool_call.params
    client_ip = request.client.host if request.client else None
    
    # Check if tool exists
    if tool_name in STUDENT_TOOLS:
        tool_fn = STUDENT_TOOLS[tool_name]
        if tool_name == "ask_reglement":
            # RAG tool needs query parameter
            return tool_fn(db, current_user.id, params.get("query", ""), params.get("top_k", 5))
        elif tool_name == "get_my_access_history":
            return tool_fn(db, current_user.id, params.get("limit", 10))
        else:
            return tool_fn(db, current_user.id)
    
    elif tool_name in ADMIN_TOOLS:
        # Admin tools require ADMIN role
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Accès réservé aux administrateurs"
            )
        
        tool_fn = ADMIN_TOOLS[tool_name]
        
        try:
            # Call with appropriate parameters
            if tool_name == "list_students":
                return tool_fn(db, current_user.id, params.get("search"), params.get("limit", 50), client_ip)
            elif tool_name == "create_student":
                return tool_fn(db, current_user.id, params["email"], params["full_name"], 
                            params.get("password", "changeme123"), client_ip)
            elif tool_name == "delete_student":
                return tool_fn(db, current_user.id, params["student_email"], client_ip)
            elif tool_name == "add_vehicle":
                return tool_fn(db, current_user.id, params["student_email"], params["plate"],
                            params.get("plate_type", "TN"), client_ip)
            elif tool_name == "remove_vehicle":
                return tool_fn(db, current_user.id, params["plate"], client_ip)
            elif tool_name == "create_subscription":
                return tool_fn(db, current_user.id, params["student_email"], params["sub_type"], client_ip)
            elif tool_name == "renew_subscription":
                return tool_fn(db, current_user.id, params["student_email"], params["days"], client_ip)
            elif tool_name == "assign_slot":
                return tool_fn(db, current_user.id, params["student_email"], params["slot_code"], client_ip)
            elif tool_name == "suspend_access":
                return tool_fn(db, current_user.id, params["student_email"], params["days"], 
                            params["reason"], client_ip)
            elif tool_name == "get_admin_stats":
                return tool_fn(db, current_user.id, client_ip)
            elif tool_name == "check_plate_access":
                return tool_fn(db, current_user.id, params["plate"], client_ip)
        except Exception as e:
            print(f"CRITICAL TOOL ERROR in {tool_name}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    raise HTTPException(
        status_code=404,
        detail=f"Outil '{tool_name}' non trouvé"
    )


@router.get("/tools")
async def list_available_tools(current_user: User = Depends(get_current_user)):
    """List available tools for current user based on role."""
    tools = list(STUDENT_TOOLS.keys())
    if current_user.role == UserRole.ADMIN:
        tools.extend(ADMIN_TOOLS.keys())
    return {"tools": tools, "role": current_user.role.value}
