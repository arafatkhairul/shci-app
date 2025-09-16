"""
Database Service for data persistence
"""
import sqlite3
from typing import Optional, Dict, Any, List
from app.config.settings import settings
from app.utils.logger import get_logger, log_exception
from app.models.roleplay import RolePlayConfig

log = get_logger("database_service")

class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DB_PATH
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create role play configs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS role_play_configs (
                    client_id TEXT PRIMARY KEY,
                    role_play_enabled BOOLEAN DEFAULT FALSE,
                    role_play_template TEXT DEFAULT 'school',
                    organization_name TEXT DEFAULT '',
                    organization_details TEXT DEFAULT '',
                    role_title TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create user memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    client_id TEXT PRIMARY KEY,
                    memory_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            log.info("Database initialized successfully")
            
        except Exception as e:
            log_exception(log, "Database initialization error", e)

    def save_role_play_config(self, config: RolePlayConfig) -> bool:
        """Save role play configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO role_play_configs 
                (client_id, role_play_enabled, role_play_template, 
                 organization_name, organization_details, role_title, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                config.client_id,
                config.role_play_enabled,
                config.role_play_template,
                config.organization_name,
                config.organization_details,
                config.role_title
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            log_exception(log, "Error saving role play config", e)
            return False

    def get_role_play_config(self, client_id: str) -> Optional[RolePlayConfig]:
        """Get role play configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT role_play_enabled, role_play_template, organization_name,
                       organization_details, role_title
                FROM role_play_configs 
                WHERE client_id = ?
            """, (client_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return RolePlayConfig(
                    client_id=client_id,
                    role_play_enabled=bool(result[0]),
                    role_play_template=result[1] or "school",
                    organization_name=result[2] or "",
                    organization_details=result[3] or "",
                    role_title=result[4] or ""
                )
            return None
            
        except Exception as e:
            log_exception(log, "Error getting role play config", e)
            return None

    def delete_role_play_config(self, client_id: str) -> bool:
        """Delete role play configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM role_play_configs WHERE client_id = ?", (client_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            log_exception(log, "Error deleting role play config", e)
            return False

    def get_all_role_play_configs(self) -> List[RolePlayConfig]:
        """Get all role play configurations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT client_id, role_play_enabled, role_play_template,
                       organization_name, organization_details, role_title
                FROM role_play_configs
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            configs = []
            for result in results:
                configs.append(RolePlayConfig(
                    client_id=result[0],
                    role_play_enabled=bool(result[1]),
                    role_play_template=result[2] or "school",
                    organization_name=result[3] or "",
                    organization_details=result[4] or "",
                    role_title=result[5] or ""
                ))
            
            return configs
            
        except Exception as e:
            log_exception(log, "Error getting all role play configs", e)
            return []

    def check_organization_exists(self, organization_name: str) -> bool:
        """Check if organization exists in any config"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM role_play_configs 
                WHERE organization_name = ?
            """, (organization_name,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            log_exception(log, "Error checking organization existence", e)
            return False

