"""
Project Management & Storage
Handles project saving, loading, and file management
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import streamlit as st

try:
    import sqlite3
except ImportError:
    sqlite3 = None


# ============================================================================
# PROJECT DATABASE
# ============================================================================

class ProjectDatabase:
    """Manage project data using SQLite"""
    
    def __init__(self, db_path: str = "projects.db"):
        """Initialize project database"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        if sqlite3 is None:
            st.error("SQLite3 is not available.")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    status TEXT DEFAULT 'in_progress'
                )
            """)
            
            # Create project files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            # Create project metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL UNIQUE,
                    input_type TEXT,
                    script_length INTEGER,
                    voiceover_duration REAL,
                    video_resolution TEXT,
                    output_format TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            st.error(f"Error initializing database: {str(e)}")
    
    def create_project(self, project_name: str, description: str = "") -> Optional[int]:
        """Create new project"""
        if sqlite3 is None:
            st.error("SQLite3 is not available.")
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO projects (project_name, description) VALUES (?, ?)",
                (project_name, description)
            )
            
            project_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return project_id
        
        except Exception as e:
            st.error(f"Error creating project: {str(e)}")
            return None
    
    def get_projects(self) -> List[Dict]:
        """Get all projects"""
        if sqlite3 is None:
            st.error("SQLite3 is not available.")
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, project_name, created_at, updated_at, description, status
                FROM projects
                ORDER BY updated_at DESC
            """)
            
            projects = []
            for row in cursor.fetchall():
                projects.append({
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "description": row[4],
                    "status": row[5]
                })
            
            conn.close()
            return projects
        
        except Exception as e:
            st.error(f"Error retrieving projects: {str(e)}")
            return []
    
    def save_project_file(
        self,
        project_id: int,
        file_type: str,
        file_path: str,
        file_name: str
    ) -> bool:
        """Save project file reference"""
        if sqlite3 is None:
            st.error("SQLite3 is not available.")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO project_files (project_id, file_type, file_path, file_name)
                   VALUES (?, ?, ?, ?)""",
                (project_id, file_type, file_path, file_name)
            )
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            st.error(f"Error saving project file: {str(e)}")
            return False
    
    def get_project_files(self, project_id: int) -> List[Dict]:
        """Get all files for a project"""
        if sqlite3 is None:
            st.error("SQLite3 is not available.")
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT id, file_type, file_path, file_name, created_at
                   FROM project_files
                   WHERE project_id = ?
                   ORDER BY created_at DESC""",
                (project_id,)
            )
            
            files = []
            for row in cursor.fetchall():
                files.append({
                    "id": row[0],
                    "type": row[1],
                    "path": row[2],
                    "name": row[3],
                    "created_at": row[4]
                })
            
            conn.close()
            return files
        
        except Exception as e:
            st.error(f"Error retrieving project files: {str(e)}")
            return []
    
    def update_project_status(self, project_id: int, status: str) -> bool:
        """Update project status"""
        if sqlite3 is None:
            st.error("SQLite3 is not available.")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, project_id)
            )
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            st.error(f"Error updating project status: {str(e)}")
            return False
    
    def delete_project(self, project_id: int) -> bool:
        """Delete project and associated files"""
        if sqlite3 is None:
            st.error("SQLite3 is not available.")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete project files
            cursor.execute("DELETE FROM project_files WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM project_metadata WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            
            conn.commit()
            conn.close()
            return True
        
        except Exception as e:
            st.error(f"Error deleting project: {str(e)}")
            return False


# ============================================================================
# PROJECT EXPORT/IMPORT
# ============================================================================

def export_project_as_json(project_data: Dict, output_path: Optional[str] = None) -> Optional[str]:
    """Export project data as JSON"""
    try:
        if not output_path:
            output_path = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    except Exception as e:
        st.error(f"Error exporting project: {str(e)}")
        return None


def import_project_from_json(json_file_path: str) -> Optional[Dict]:
    """Import project data from JSON"""
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)
        
        return project_data
    
    except Exception as e:
        st.error(f"Error importing project: {str(e)}")
        return None


# ============================================================================
# PROJECT UTILITIES
# ============================================================================

def create_project_directory(project_name: str) -> str:
    """Create project directory"""
    project_dir = Path(f"projects/{project_name}")
    project_dir.mkdir(parents=True, exist_ok=True)
    return str(project_dir)


def get_project_size(project_dir: str) -> int:
    """Get total size of project directory in bytes"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(project_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size


def format_file_size(size_bytes: int) -> str:
    """Format file size to human-readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_project_summary(project_data: Dict) -> Dict:
    """Generate project summary"""
    return {
        "project_name": project_data.get("project_name", "Unknown"),
        "created_at": project_data.get("created_at", "Unknown"),
        "status": project_data.get("status", "unknown"),
        "input_type": project_data.get("input_type", "Unknown"),
        "script_length": project_data.get("script_length", 0),
        "voiceover_duration": project_data.get("voiceover_duration", 0),
        "video_resolution": project_data.get("video_resolution", "Unknown"),
        "output_format": project_data.get("output_format", "MP4")
    }


# ============================================================================
# BACKUP & RECOVERY
# ============================================================================

def backup_project(project_dir: str, backup_dir: str = "backups") -> Optional[str]:
    """Create backup of project"""
    try:
        import shutil
        
        backup_path = Path(backup_dir) / f"{Path(project_dir).name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree(project_dir, backup_path)
        
        return str(backup_path)
    
    except Exception as e:
        st.error(f"Error creating backup: {str(e)}")
        return None


def cleanup_old_backups(backup_dir: str = "backups", keep_count: int = 5):
    """Clean up old backups, keeping only the most recent ones"""
    try:
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return
        
        # Get all backup directories sorted by modification time
        backups = sorted(
            backup_path.iterdir(),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # Remove old backups
        for backup in backups[keep_count:]:
            import shutil
            shutil.rmtree(backup)
    
    except Exception as e:
        st.error(f"Error cleaning up backups: {str(e)}")
