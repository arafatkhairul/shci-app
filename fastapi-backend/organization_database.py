#!/usr/bin/env python3
"""
Organization Database Management
Handles organization creation, validation, and storage
"""

import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

log = logging.getLogger("organization_db")

class OrganizationDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with organizations table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create organizations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS organizations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        details TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for faster lookups
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_org_name ON organizations(name)")
                
                conn.commit()
                log.info("Organization database initialized successfully")
                
        except Exception as e:
            log.error(f"Organization database initialization error: {e}")
            raise
    
    def create_organization(self, name: str, details: str = '') -> Dict[str, Any]:
        """Create a new organization with unique name validation"""
        try:
            # Validate organization name
            if not name or not name.strip():
                return {"success": False, "error": "Organization name is required"}
            
            name = name.strip()
            if len(name) < 2:
                return {"success": False, "error": "Organization name must be at least 2 characters long"}
            
            if len(name) > 100:
                return {"success": False, "error": "Organization name must be less than 100 characters"}
            
            # Check if organization already exists
            if self.organization_exists(name):
                return {"success": False, "error": "Organization name already exists"}
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO organizations (name, details)
                    VALUES (?, ?)
                """, (name, details.strip()))
                
                org_id = cursor.lastrowid
                conn.commit()
                
                log.info(f"Created organization: {name} (ID: {org_id})")
                
                return {
                    "success": True,
                    "organization": {
                        "id": org_id,
                        "name": name,
                        "details": details.strip(),
                        "created_at": time.time()
                    }
                }
                
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Organization name already exists"}
        except Exception as e:
            log.error(f"Create organization error for {name}: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    def organization_exists(self, name: str) -> bool:
        """Check if organization name already exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT id FROM organizations WHERE LOWER(name) = LOWER(?)", (name.strip(),))
                return cursor.fetchone() is not None
                
        except Exception as e:
            log.error(f"Check organization exists error for {name}: {e}")
            return False
    
    def get_organization(self, name: str) -> Optional[Dict[str, Any]]:
        """Get organization by name"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, name, details, created_at, updated_at
                    FROM organizations 
                    WHERE LOWER(name) = LOWER(?)
                """, (name.strip(),))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'details': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    }
                return None
                
        except Exception as e:
            log.error(f"Get organization error for {name}: {e}")
            return None
    
    def get_organization_by_id(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Get organization by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, name, details, created_at, updated_at
                    FROM organizations 
                    WHERE id = ?
                """, (org_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'details': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    }
                return None
                
        except Exception as e:
            log.error(f"Get organization by ID error for {org_id}: {e}")
            return None
    
    def update_organization(self, org_id: int, name: str = None, details: str = None) -> Dict[str, Any]:
        """Update organization details"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if organization exists
                if not self.get_organization_by_id(org_id):
                    return {"success": False, "error": "Organization not found"}
                
                # Validate name if provided
                if name is not None:
                    name = name.strip()
                    if not name:
                        return {"success": False, "error": "Organization name cannot be empty"}
                    
                    if len(name) < 2:
                        return {"success": False, "error": "Organization name must be at least 2 characters long"}
                    
                    if len(name) > 100:
                        return {"success": False, "error": "Organization name must be less than 100 characters"}
                    
                    # Check if new name already exists (excluding current org)
                    cursor.execute("SELECT id FROM organizations WHERE LOWER(name) = LOWER(?) AND id != ?", (name, org_id))
                    if cursor.fetchone():
                        return {"success": False, "error": "Organization name already exists"}
                
                # Build update query
                update_fields = []
                update_values = []
                
                if name is not None:
                    update_fields.append("name = ?")
                    update_values.append(name)
                
                if details is not None:
                    update_fields.append("details = ?")
                    update_values.append(details.strip())
                
                if not update_fields:
                    return {"success": False, "error": "No fields to update"}
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(org_id)
                
                query = f"UPDATE organizations SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, update_values)
                
                conn.commit()
                
                log.info(f"Updated organization ID {org_id}")
                
                return {
                    "success": True,
                    "message": "Organization updated successfully"
                }
                
        except Exception as e:
            log.error(f"Update organization error for ID {org_id}: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    def get_all_organizations(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all organizations with pagination"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, name, details, created_at, updated_at
                    FROM organizations 
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                rows = cursor.fetchall()
                return [
                    {
                        'id': row[0],
                        'name': row[1],
                        'details': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            log.error(f"Get all organizations error: {e}")
            return []
    
    def delete_organization(self, org_id: int) -> Dict[str, Any]:
        """Delete organization by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if organization exists
                org = self.get_organization_by_id(org_id)
                if not org:
                    return {"success": False, "error": "Organization not found"}
                
                cursor.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
                conn.commit()
                
                log.info(f"Deleted organization: {org['name']} (ID: {org_id})")
                
                return {
                    "success": True,
                    "message": f"Organization '{org['name']}' deleted successfully"
                }
                
        except Exception as e:
            log.error(f"Delete organization error for ID {org_id}: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    def get_organization_stats(self) -> Dict[str, Any]:
        """Get organization database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count total organizations
                cursor.execute("SELECT COUNT(*) FROM organizations")
                total_orgs = cursor.fetchone()[0]
                
                # Count organizations with details
                cursor.execute("SELECT COUNT(*) FROM organizations WHERE details != ''")
                orgs_with_details = cursor.fetchone()[0]
                
                # Get recent organizations
                cursor.execute("""
                    SELECT name, created_at 
                    FROM organizations 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                recent_orgs = cursor.fetchall()
                
                return {
                    'total_organizations': total_orgs,
                    'organizations_with_details': orgs_with_details,
                    'recent_organizations': [
                        {'name': row[0], 'created_at': row[1]} 
                        for row in recent_orgs
                    ]
                }
                
        except Exception as e:
            log.error(f"Get organization stats error: {e}")
            return {}
