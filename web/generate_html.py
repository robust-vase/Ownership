import json
from pathlib import Path
from main_page_generator import generate_main_page_html

def read_scene_data(json_file_path):
    """Read scene data JSON file"""
    print(f"[DEBUG] Reading scene data from: {json_file_path}")
    print(f"[DEBUG] File exists: {json_file_path.exists()}")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"[DEBUG] Scene data loaded successfully")
    return data

def save_html(html_content, output_path):
    """Save HTML file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[INFO] HTML file saved to: {output_path}")

def scan_scene_folders(base_path):
    """Scan for all scene folders in the base directory"""
    scene_folders = []
    if base_path.exists():
        for folder in sorted(base_path.iterdir()):
            if folder.is_dir() and folder.name.startswith('table_scene_'):
                scene_data_file = folder / 'scene_data.json'
                if scene_data_file.exists():
                    scene_folders.append(folder.name)
    return scene_folders

def main():
    print("\n" + "=" * 60)
    print("Dashboard HTML Generator")
    print("=" * 60 + "\n")
    
    # Set file paths
    current_dir = Path(__file__).parent
    base_logs_path = current_dir.parent / 'logs' / '4agents_9_allmap'
    
    # Scan all available scene folders
    scene_folders = scan_scene_folders(base_logs_path)
    print(f"[INFO] Found {len(scene_folders)} scene folders:")
    for folder in scene_folders:
        print(f"  - {folder}")
    print()
    
    # Use first scene as default
    default_scene = scene_folders[0] if scene_folders else 'table_scene_map001_room_diningRoom_table1'
    sample_json_path = base_logs_path / default_scene / 'scene_data.json'
    images_directory = base_logs_path / default_scene
    output_html_path = current_dir / 'dashboard.html'
    
    print(f"[INFO] Configuration:")
    print(f"  Scene JSON: {sample_json_path}")
    print(f"  Images Dir: {images_directory}")
    print(f"  Output HTML: {output_html_path}")
    print(f"\n[INFO] Checking paths...")
    print(f"  Scene JSON exists: {sample_json_path.exists()}")
    print(f"  Images Dir exists: {images_directory.exists()}")
    print()
    
    # Read JSON data
    scene_data = read_scene_data(sample_json_path)
    
    # Generate main page HTML with scene list
    html_content = generate_main_page_html(scene_data, images_directory, scene_folders, default_scene)
    save_html(html_content, output_html_path)
    
    print("\n" + "=" * 60)
    print("Dashboard HTML Generated Successfully!")
    print("=" * 60)
    print(f"\nOutput file: {output_html_path}")
    print("\nNext steps:")
    print("  1. Start the server: python server.py")
    print("  2. Open browser: http://localhost:5000/dashboard.html")
    print()

if __name__ == "__main__":
    main()