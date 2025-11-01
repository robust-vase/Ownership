"""
Object Ownership Management Module
Handles saving and loading object-person ownership relationships
"""
import json
from pathlib import Path
from datetime import datetime


class OwnershipManager:
    """Object Ownership Manager"""
    
    def __init__(self, save_directory="ownership_data", scene_name=None):
        """
        Initialize manager
        
        Args:
            save_directory: Directory path for saving data
            scene_name: Scene folder name (used to create scene-specific subfolder)
        """
        self.save_directory = Path(save_directory)
        
        # Create scene-specific subfolder if scene_name provided
        if scene_name:
            self.save_directory = self.save_directory / scene_name
        
        self.save_directory.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] OwnershipManager initialized, save directory: {self.save_directory.absolute()}")
    
    def save_all_ownerships(self, ownership_list, session_id=None):
        """
        Batch save all object ownership relationships
        
        Args:
            ownership_list: List of ownership relationships, each containing:
                {
                    "object_id": str,
                    "object_name": str,
                    "owner_id": str,
                    "owner_name": str
                }
            session_id: Session ID (optional, used to identify same batch data)
        
        Returns:
            Saved file path
        """
        if not ownership_list:
            print("[WARNING] No ownership relationships to save")
            return None
        
        # Auto-generate session_id if not provided
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        timestamp = datetime.now().isoformat()
        
        # Build complete data structure
        batch_data = {
            "session_id": session_id,
            "timestamp": timestamp,
            "total_count": len(ownership_list),
            "ownerships": []
        }
        
        # Add all ownership relationships
        for ownership in ownership_list:
            batch_data["ownerships"].append({
                "object_id": ownership.get("object_id"),
                "object_name": ownership.get("object_name"),
                "owner_id": ownership.get("owner_id"),
                "owner_name": ownership.get("owner_name"),
                "timestamp": timestamp
            })
        
        # Save to batch file
        filename = f"ownership_batch_{session_id}.json"
        filepath = self.save_directory / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, indent=2, ensure_ascii=False)
        
        print(f"[SUCCESS] Batch saved {len(ownership_list)} ownership relationships")
        print(f"[SUCCESS] File saved to: {filepath.absolute()}")
        return str(filepath)
    
    def load_ownership_batch(self, session_id):
        """
        Load ownership relationships for specified session
        
        Args:
            session_id: Session ID
        
        Returns:
            Ownership data dictionary, None if not exists
        """
        filename = f"ownership_batch_{session_id}.json"
        filepath = self.save_directory / filename
        
        if not filepath.exists():
            print(f"[WARNING] Session data not found: {session_id}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"[SUCCESS] Loaded session data: {session_id} ({data['total_count']} relationships)")
        return data
    
    def list_all_sessions(self):
        """
        List all saved sessions
        
        Returns:
            List of session information
        """
        sessions = []
        
        for filepath in self.save_directory.glob("ownership_batch_*.json"):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "timestamp": data["timestamp"],
                    "total_count": data["total_count"],
                    "filepath": str(filepath)
                })
        
        sessions.sort(key=lambda x: x["timestamp"], reverse=True)
        return sessions
    
    def export_to_simple_format(self, session_id, output_path=None):
        """
        Export to simplified format (ID mapping only)
        
        Args:
            session_id: Session ID
            output_path: Output file path (optional)
        
        Returns:
            Simplified data dictionary {object_id: owner_id}
        """
        data = self.load_ownership_batch(session_id)
        if not data:
            return None
        
        # Build simplified mapping
        simple_mapping = {}
        for ownership in data["ownerships"]:
            simple_mapping[ownership["object_id"]] = ownership["owner_id"]
        
        # Save to file if output path specified
        if output_path:
            output_path = Path(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(simple_mapping, f, indent=2, ensure_ascii=False)
            print(f"[SUCCESS] Exported simplified mapping to: {output_path}")
        
        return simple_mapping



# Convenience function for web interface
def save_all_ownerships_from_web(data):
    """
    Batch save ownership relationships from web request
    
    Args:
        data: Dictionary containing ownerships list, optional session_id, and optional scene_name
    
    Returns:
        Save result
    """
    try:
        scene_name = data.get("scene_name")
        manager = OwnershipManager(scene_name=scene_name)
        
        ownerships = data.get("ownerships", [])
        session_id = data.get("session_id")
        
        print(f"[DEBUG] Received {len(ownerships)} ownerships to save")
        if scene_name:
            print(f"[DEBUG] Scene name: {scene_name}")
        
        # Ensure each ownership has necessary fields
        processed_ownerships = []
        for ownership in ownerships:
            processed_ownerships.append({
                "object_id": ownership["object_id"],
                "object_name": ownership.get("object_name", "Unknown"),
                "owner_id": ownership.get("owner_id", ownership.get("owner_name")),
                "owner_name": ownership["owner_name"]
            })
        
        filepath = manager.save_all_ownerships(processed_ownerships, session_id)
        
        return {
            "success": True,
            "filepath": filepath,
            "count": len(processed_ownerships),
            "session_id": session_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
            "scene_name": scene_name,
            "message": f"Saved {len(processed_ownerships)} ownership relationships"
        }
    except Exception as e:
        print(f"[ERROR] Failed to batch save ownerships: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to save ownerships"
        }


# Test code
if __name__ == "__main__":
    manager = OwnershipManager("test_ownership_data")
    
    # Test batch save
    print("\n=== Test: Batch Save ===")
    test_ownerships = [
        {
            "object_id": "BP_Toy_garras_C_2147051301",
            "object_name": "Toy",
            "owner_id": "SDBP_Aich_AIBaby_Lele_Shoes_1",
            "owner_name": "Girl"
        },
        {
            "object_id": "BP_Food_Donut_4_C_2147051299",
            "object_name": "Donut",
            "owner_id": "SDBP_Aich_Yeye_3",
            "owner_name": "Grandpa"
        },
        {
            "object_id": "BP_Book_01_C_2147051298",
            "object_name": "Book",
            "owner_id": "public",
            "owner_name": "Public"
        }
    ]
    
    session_id = "test_session_001"
    filepath = manager.save_all_ownerships(test_ownerships, session_id)
    
    # Test loading
    print("\n=== Test: Load Data ===")
    loaded_data = manager.load_ownership_batch(session_id)
    print(f"Loaded data: {json.dumps(loaded_data, indent=2, ensure_ascii=False)}")
    
    # Test list all sessions
    print("\n=== Test: List All Sessions ===")
    sessions = manager.list_all_sessions()
    for session in sessions:
        print(f"  Session: {session['session_id']}, Time: {session['timestamp']}, Count: {session['total_count']}")
    
    # Test export to simple format
    print("\n=== Test: Export Simple Format ===")
    simple_map = manager.export_to_simple_format(session_id, "test_simple_mapping.json")
    print(f"Simple mapping: {json.dumps(simple_map, indent=2, ensure_ascii=False)}")

