"""
Data Processor
==============
Centralized scene data processing logic.
Shared by page_generators.py and guide_page_generator.py.
"""
import json
import sys
from pathlib import Path
from collections import Counter

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.projection_util import prepare_camera_params, project_aabb_to_polygon, get_agent_label_position, get_agent_hull
from core.translations import get_text, TRANSLATIONS
from config import EXCLUDED_TYPES, AGENT_BLUEPRINT_MAPPING, ROLE_COLORS, DISPLAY_CATEGORY_MAPPING


def _get_agent_role_from_blueprint(blueprint_id):
    """Determine agent role from blueprint ID."""
    for role, blueprints in AGENT_BLUEPRINT_MAPPING.items():
        if any(bp in blueprint_id for bp in blueprints):
            return role
    return 'person'


def _translate_agent_role(role, lang='en'):
    """Translate agent role to display name based on language."""
    agent_roles = TRANSLATIONS.get('agent_roles', {})
    if role in agent_roles:
        return agent_roles[role].get(lang, agent_roles[role].get('en', role.title()))
    return role.title()


def _translate_object_category(category, lang='en'):
    """Translate object category to display name based on language."""
    object_categories = TRANSLATIONS.get('object_categories', {})
    # Try exact match first
    if category in object_categories:
        return object_categories[category].get(lang, object_categories[category].get('en', category))
    # Try title case (e.g., 'toy' -> 'Toy')
    title_category = category.title()
    if title_category in object_categories:
        return object_categories[title_category].get(lang, object_categories[title_category].get('en', category))
    return category


def _generate_agent_color(agent_id, agent_base_id=None):
    """Generate fixed color based on agent blueprint/role."""
    if agent_base_id:
        role = _get_agent_role_from_blueprint(agent_base_id)
        if role in ROLE_COLORS:
            return ROLE_COLORS[role]
    return '#808080'


def _deduplicate_names(items, name_key='base_name', output_key='display_name'):
    """
    Generic deduplication for objects/agents.
    Adds numbered suffix if there are multiple items with the same name.
    """
    name_counts = Counter([item[name_key] for item in items])
    name_current = {}
    
    for item in items:
        name = item[name_key]
        if name_counts[name] > 1:
            if name not in name_current:
                name_current[name] = 1
            item[output_key] = f"{name}_{name_current[name]}"
            name_current[name] += 1
        else:
            item[output_key] = name


def process_scene_objects(scene_data, rotation_matrix, intrinsic_matrix, camera_location, 
                          use_display_mapping=True, filter_empty_plates=True):
    """
    Process and project objects from scene data.
    
    Args:
        scene_data: Raw scene data dict
        rotation_matrix: Camera rotation matrix
        intrinsic_matrix: Camera intrinsic matrix  
        camera_location: Camera position
        use_display_mapping: If True, use DISPLAY_CATEGORY_MAPPING for display names
        filter_empty_plates: If True, skip objects with type 'plate'
    
    Returns:
        List of processed object dicts with polygon projections
    """
    objects_data = []
    
    for obj in scene_data.get('objects', []):
        obj_id = obj.get('id', 'unknown')
        owner = obj.get('owner', '').lower()
        
        # Skip room-owned objects
        if owner == 'room':
            continue
        
        obj_type = obj.get('type', obj.get('base_id', 'unknown'))
        if obj_type in EXCLUDED_TYPES:
            continue
        
        if 'entity_min' not in obj or 'entity_max' not in obj:
            continue
        
        try:
            polygon = project_aabb_to_polygon(
                obj['entity_min'], obj['entity_max'],
                rotation_matrix, intrinsic_matrix, camera_location
            )
            
            if polygon:
                raw_type = obj.get('my_type', obj_type).lower()
                
                # Filter out empty plates
                if filter_empty_plates and raw_type == 'plate':
                    continue
                
                if use_display_mapping:
                    display_category = DISPLAY_CATEGORY_MAPPING.get(raw_type, raw_type.title())
                    objects_data.append({
                        'id': obj_id,
                        'raw_type': raw_type,
                        'display_category': display_category,
                        'base_name': display_category,  # For deduplication
                        'polygon': polygon,
                        'owner': owner
                    })
                else:
                    objects_data.append({
                        'id': obj_id,
                        'base_name': raw_type,
                        'polygon': polygon,
                        'owner': owner
                    })
        except Exception as e:
            print(f"[WARNING] Failed to project object {obj_id}: {e}")
            continue
    
    return objects_data


def process_scene_agents(scene_data, rotation_matrix, intrinsic_matrix, camera_location):
    """
    Process and project agents from scene data.
    
    Args:
        scene_data: Raw scene data dict
        rotation_matrix: Camera rotation matrix
        intrinsic_matrix: Camera intrinsic matrix
        camera_location: Camera position
    
    Returns:
        Tuple of (agents_data, agent_labels)
    """
    agents_data = []
    agent_labels = []
    
    for agent in scene_data.get('agents', []):
        agent_id = agent.get('id', 'unknown')
        agent_type = agent.get('type', agent.get('base_id', 'person')).lower()
        agent_base_id = agent.get('base_id', '')
        
        color = _generate_agent_color(agent_id, agent_base_id)
        
        # Project label position
        try:
            pixel = get_agent_label_position(agent, rotation_matrix, intrinsic_matrix, camera_location)
            if pixel:
                agent_labels.append({
                    'id': agent_id,
                    'type': agent_type,
                    'x': pixel[0],
                    'y': pixel[1] - 40,
                    'color': color
                })
        except:
            pass
        
        # Project hull
        hull_points = None
        try:
            hull_points = get_agent_hull(agent, rotation_matrix, intrinsic_matrix, camera_location)
        except:
            pass
        
        agents_data.append({
            'id': agent_id,
            'type': agent_type,
            'color': color,
            'hull': hull_points
        })
    
    return agents_data, agent_labels


def process_scene_data(scene_data, camera_data, use_display_mapping=True, filter_empty_plates=True, lang='en'):
    """
    Complete scene data processing pipeline.
    
    Args:
        scene_data: Raw scene data dict
        camera_data: Camera parameters dict
        use_display_mapping: If True, use DISPLAY_CATEGORY_MAPPING for object names
        filter_empty_plates: If True, skip plate objects
        lang: Language code ('en' or 'zh') for display names
    
    Returns:
        Tuple of (objects_data, agents_data, agent_labels) - all with display_name set
    """
    # Prepare camera matrices
    rotation_matrix, intrinsic_matrix, camera_location = prepare_camera_params(camera_data)
    
    # Process objects
    objects_data = process_scene_objects(
        scene_data, rotation_matrix, intrinsic_matrix, camera_location,
        use_display_mapping=use_display_mapping,
        filter_empty_plates=filter_empty_plates
    )
    
    # Deduplicate object names (using English keys first for consistency)
    name_key = 'display_category' if use_display_mapping else 'base_name'
    _deduplicate_names(objects_data, name_key=name_key, output_key='display_name')
    
    # Translate object display names based on language
    for obj in objects_data:
        base_name = obj['display_name']
        # Check if it has a numbered suffix (e.g., "Toy_1")
        if '_' in base_name and base_name.split('_')[-1].isdigit():
            parts = base_name.rsplit('_', 1)
            translated_base = _translate_object_category(parts[0], lang)
            obj['display_name'] = f"{translated_base}_{parts[1]}"
        else:
            obj['display_name'] = _translate_object_category(base_name, lang)
    
    # Process agents
    agents_data, agent_labels = process_scene_agents(
        scene_data, rotation_matrix, intrinsic_matrix, camera_location
    )
    
    # Deduplicate agent names (using English type keys first)
    _deduplicate_names(agents_data, name_key='type', output_key='display_name')
    _deduplicate_names(agent_labels, name_key='type', output_key='display_name')
    
    # Translate agent display names based on language
    for agent in agents_data:
        base_name = agent['display_name']
        # Check if it has a numbered suffix (e.g., "boy_1")
        if '_' in base_name:
            parts = base_name.rsplit('_', 1)
            if parts[-1].isdigit():
                translated_base = _translate_agent_role(parts[0], lang)
                agent['display_name'] = f"{translated_base}_{parts[1]}"
            else:
                # No suffix, just translate the whole thing
                agent['display_name'] = _translate_agent_role(base_name, lang)
        else:
            agent['display_name'] = _translate_agent_role(base_name, lang)
    
    for label in agent_labels:
        base_name = label['display_name']
        if '_' in base_name:
            parts = base_name.rsplit('_', 1)
            if parts[-1].isdigit():
                translated_base = _translate_agent_role(parts[0], lang)
                label['display_name'] = f"{translated_base}_{parts[1]}"
            else:
                label['display_name'] = _translate_agent_role(base_name, lang)
        else:
            label['display_name'] = _translate_agent_role(base_name, lang)
    
    return objects_data, agents_data, agent_labels
