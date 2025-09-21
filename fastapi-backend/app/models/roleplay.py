"""
Role Play Models
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class RolePlayConfig:
    """Role play configuration model"""
    client_id: str
    role_play_enabled: bool = False
    role_play_template: str = "school"
    organization_name: str = ""
    organization_details: str = ""
    role_title: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "client_id": self.client_id,
            "role_play_enabled": self.role_play_enabled,
            "role_play_template": self.role_play_template,
            "organization_name": self.organization_name,
            "organization_details": self.organization_details,
            "role_title": self.role_title
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RolePlayConfig":
        """Create from dictionary"""
        return cls(
            client_id=data["client_id"],
            role_play_enabled=data.get("role_play_enabled", False),
            role_play_template=data.get("role_play_template", "school"),
            organization_name=data.get("organization_name", ""),
            organization_details=data.get("organization_details", ""),
            role_title=data.get("role_title", "")
        )

