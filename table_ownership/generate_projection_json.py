import os
import json
import shutil
import glob
import numpy as np
from PIL import Image
from ground_truth import (
    prepare_camera_parameters,
    project_agent_to_image,
    project_aabb_to_image
)

def create_projection_json(original_data, camera_idx, camera_data, image_width=4096, image_height=4096):
    """为单个相机视角创建投影后的JSON数据"""
    projected_data = {
        "scene_info": {},
        "objects": [],
        "agents": [],
        "cameras": [camera_data]  # 只包含当前相机
    }

    # 处理场景信息
    scene_info = original_data["scene_info"].copy()
    # 投影场景AABB边界框
    aabb_bbox, _ = project_aabb_to_image(scene_info["aabb_bounds"], camera_data, image_width, image_height)
    if aabb_bbox:
        x_min, y_min, x_max, y_max = aabb_bbox
        scene_info["aabb_bounds"] = {
            "min": {"x": x_min, "y": y_min},
            "max": {"x": x_max, "y": y_max}
        }
    
    # 投影场景中心点
    center_pos = project_agent_to_image(scene_info["position"], camera_data, image_width, image_height)
    if center_pos:
        x, y = center_pos
        scene_info["position"] = {"x": x, "y": y}
    
    projected_data["scene_info"] = scene_info

    # 处理物体
    for obj in original_data["objects"]:
        projected_obj = {
            "id": obj["id"],
            "base_id": obj["base_id"],
            "type": obj["type"],
            "owner": obj.get("owner", "unknown"),
            "asset_type": obj.get("asset_type", "unknown")
        }
        
        if "features" in obj:
            projected_obj["features"] = obj["features"]

        # 投影物体中心点
        center_pos = project_agent_to_image(obj["position"], camera_data, image_width, image_height)
        if center_pos:
            x, y = center_pos
            projected_obj["position"] = {"x": x, "y": y}

        # 投影物体AABB边界框
        if "aabb_bounds" in obj:
            aabb_bbox, _ = project_aabb_to_image(obj["aabb_bounds"], camera_data, image_width, image_height)
            if aabb_bbox:
                x_min, y_min, x_max, y_max = aabb_bbox
                projected_obj["aabb_bounds"] = {
                    "min": {"x": x_min, "y": y_min},
                    "max": {"x": x_max, "y": y_max}
                }
        
        projected_data["objects"].append(projected_obj)

    # 处理agents
    for agent in original_data["agents"]:
        projected_agent = {
            "id": agent["id"],
            "base_id": agent["base_id"],
            "type": agent["type"]
        }
        
        if "features" in agent:
            projected_agent["features"] = agent["features"]

        # 投影agent位置
        pos = project_agent_to_image(agent["position"], camera_data, image_width, image_height)
        if pos:
            x, y = pos
            projected_agent["position"] = {"x": x, "y": y}
        
        projected_data["agents"].append(projected_agent)

    return projected_data

def process_scene_folder(scene_folder):
    """处理单个场景文件夹，生成所有相机视角的投影JSON"""
    try:
        # 读取原始场景数据
        scene_data_path = os.path.join(scene_folder, "scene_data.json")
        if not os.path.exists(scene_data_path):
            print(f"错误: 场景数据文件不存在: {scene_data_path}")
            return False

        with open(scene_data_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)

        # 查找所有rgb图片
        rgb_images = glob.glob(os.path.join(scene_folder, "*rgb.png"))
        if not rgb_images:
            print(f"错误: 未找到RGB图片: {scene_folder}")
            return False

        # 创建输出目录
        output_dir = os.path.join(scene_folder, "projection_data")
        os.makedirs(output_dir, exist_ok=True)

        # 为每个相机视角生成投影数据
        for img_idx, image_path in enumerate(rgb_images):
            if img_idx >= len(original_data["cameras"]):
                print(f"警告: 图片 {img_idx+1} 没有对应的相机数据")
                continue

            camera_data = original_data["cameras"][img_idx]
            
            # 读取图片尺寸
            with Image.open(image_path) as img:
                image_width, image_height = img.size

            # 生成投影数据
            projected_data = create_projection_json(
                original_data, 
                img_idx, 
                camera_data, 
                image_width, 
                image_height
            )

            # 创建相机视角子目录
            camera_dir = os.path.join(output_dir, f"camera_{img_idx+1}")
            os.makedirs(camera_dir, exist_ok=True)

            # 保存投影JSON
            json_filename = f"projection_data.json"
            json_path = os.path.join(camera_dir, json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(projected_data, f, indent=2, ensure_ascii=False)

            # 复制对应的RGB图片
            img_filename = os.path.basename(image_path)
            shutil.copy2(image_path, os.path.join(camera_dir, img_filename))

            print(f"✅ 相机 {img_idx+1} 投影数据已生成: {json_path}")

        return True

    except Exception as e:
        print(f"处理场景文件夹时出错: {e}")
        return False

def batch_process_scenes(base_path):
    """批量处理所有场景文件夹"""
    # 查找所有包含scene_data.json的文件夹
    json_pattern = os.path.join(base_path, "**", "scene_data.json")
    json_files = glob.glob(json_pattern, recursive=True)

    print(f"找到 {len(json_files)} 个场景数据文件")

    results = {
        'total_scenes': len(json_files),
        'successful': 0,
        'failed': 0,
        'processed_folders': []
    }

    for json_file in json_files:
        scene_folder = os.path.dirname(json_file)
        folder_name = os.path.basename(scene_folder)

        print(f"\n处理场景: {folder_name}")
        success = process_scene_folder(scene_folder)

        if success:
            results['successful'] += 1
            status = 'success'
        else:
            results['failed'] += 1
            status = 'failed'

        results['processed_folders'].append({
            'folder': folder_name,
            'status': status
        })

    # 打印统计信息
    print(f"\n{'='*80}")
    print("批量处理完成统计:")
    print(f"{'='*80}")
    print(f"总场景数: {results['total_scenes']}")
    print(f"成功处理: {results['successful']}")
    print(f"处理失败: {results['failed']}")
    print(f"成功率: {(results['successful']/results['total_scenes']*100):.1f}%")

    # 打印详细结果
    print(f"\n详细处理结果:")
    for item in results['processed_folders']:
        status_icon = "✅" if item['status'] == 'success' else "❌"
        print(f"{status_icon} {item['folder']}: {item['status']}")

    return results

if __name__ == "__main__":
    base_path = "./ownership/4agents_2_allmap/"
    batch_process_scenes(base_path)