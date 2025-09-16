"""
Role Play Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.services.database_service import DatabaseService
from app.models.roleplay import RolePlayConfig
from app.utils.logger import get_logger, log_exception

log = get_logger("roleplay_endpoints")
router = APIRouter()
db_service = DatabaseService()

class RolePlayConfigRequest(BaseModel):
    client_id: str
    role_play_enabled: bool = False
    role_play_template: str = "school"
    organization_name: str = ""
    organization_details: str = ""
    role_title: str = ""

class RolePlayConfigResponse(BaseModel):
    status: str
    message: str
    config: Optional[RolePlayConfig] = None

@router.post("/config", response_model=RolePlayConfigResponse)
async def save_role_play_config(request: RolePlayConfigRequest):
    """Save role play configuration"""
    try:
        config = RolePlayConfig(
            client_id=request.client_id,
            role_play_enabled=request.role_play_enabled,
            role_play_template=request.role_play_template,
            organization_name=request.organization_name,
            organization_details=request.organization_details,
            role_title=request.role_title
        )
        
        success = db_service.save_role_play_config(config)
        
        if success:
            return RolePlayConfigResponse(
                status="success",
                message="Role play configuration saved successfully",
                config=config
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save role play configuration")
            
    except Exception as e:
        log_exception(log, "Save role play config error", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/{client_id}", response_model=RolePlayConfigResponse)
async def get_role_play_config(client_id: str):
    """Get role play configuration"""
    try:
        config = db_service.get_role_play_config(client_id)
        
        if config:
            return RolePlayConfigResponse(
                status="success",
                message="Role play configuration retrieved successfully",
                config=config
            )
        else:
            return RolePlayConfigResponse(
                status="not_found",
                message="No role play configuration found for this client",
                config=None
            )
            
    except Exception as e:
        log_exception(log, "Get role play config error", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/config/{client_id}")
async def delete_role_play_config(client_id: str):
    """Delete role play configuration"""
    try:
        success = db_service.delete_role_play_config(client_id)
        
        if success:
            return {
                "status": "success",
                "message": "Role play configuration deleted successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete role play configuration")
            
    except Exception as e:
        log_exception(log, "Delete role play config error", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs")
async def get_all_role_play_configs():
    """Get all role play configurations"""
    try:
        configs = db_service.get_all_role_play_configs()
        
        return {
            "status": "success",
            "message": f"Retrieved {len(configs)} role play configurations",
            "configs": [config.to_dict() for config in configs]
        }
        
    except Exception as e:
        log_exception(log, "Get all role play configs error", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-organization/{organization_name}")
async def check_organization_exists(organization_name: str):
    """Check if organization exists"""
    try:
        exists = db_service.check_organization_exists(organization_name)
        
        return {
            "status": "success",
            "organization_name": organization_name,
            "exists": exists
        }
        
    except Exception as e:
        log_exception(log, "Check organization error", e)
        raise HTTPException(status_code=500, detail=str(e))

