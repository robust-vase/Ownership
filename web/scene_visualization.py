import json
from pathlib import Path
import math

# 人物蓝图映射
blueprint_mapping = {
    'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes"],
    'boy': ["SDBP_Aich_AIBaby_Tiantian_90"],
    'woman': ["SDBP_Aich_Liyuxia"],
    'grandpa': ["SDBP_Aich_Yeye"],
    'man': ["SDBP_Aich_Zhanghaoran"]
}

def create_reverse_blueprint_mapping():
    reverse_mapping = {}
    for role, blueprints in blueprint_mapping.items():
        for i, blueprint in enumerate(blueprints, 1):
            if len(blueprints) > 1:
                reverse_mapping[blueprint] = f"{role}_{i}"
            else:
                reverse_mapping[blueprint] = role
    return reverse_mapping

def get_object_display_type(obj):
    if 'features' in obj and 'type' in obj['features']:
        return obj['features']['type']
    return obj.get('asset_type', 'unknown')

def quaternion_to_direction_vector(x, y, z, w):
    forward_x = 2 * (x*z + w*y)
    forward_y = 2 * (y*z - w*x)
    forward_z = 1 - 2 * (x*x + y*y)
    return forward_x, forward_y, forward_z

def determine_label_position(obj_index, objects, threshold=20):
    """确定标签位置"""
    current_obj = objects[obj_index]
    if 'aabb_bounds' not in current_obj:
        return {'position': 'top', 'offset_y': -8}
    
    current_aabb = current_obj['aabb_bounds']
    current_y = current_aabb['min']['y']
    
    # 找出所有上方的物体
    objects_above = []
    for i, other_obj in enumerate(objects):
        if i == obj_index:
            continue
        if 'aabb_bounds' not in other_obj:
            continue
        
        other_aabb = other_obj['aabb_bounds']
        other_y = other_aabb['max']['y']
        
        if other_y < current_y:
            y_distance = current_y - other_y
            if y_distance < threshold:
                objects_above.append((i, y_distance))
    
    if not objects_above:
        return {'position': 'top', 'offset_y': -8}
    
    return {'position': 'bottom', 'offset_y': 8}

def adjust_simple_label_position(labels, min_distance=30):
    """简单的标签位置避让函数"""
    for i, label in enumerate(labels):
        label['offset_y'] = 15
        
        for j, other in enumerate(labels):
            if i != j:
                dx = label['x'] - other['x']
                dy = label['y'] - other['y']
                distance = math.sqrt(dx*dx + dy*dy)
                if distance < min_distance:
                    if label['y'] < other['y']:
                        label['offset_y'] = -25
                    else:
                        label['offset_y'] = 35

def process_scene_data(data):
    """处理场景数据，转换为前端可用的格式"""
    scene_info = data['scene_info']
    objects = data['objects']
    agents = data['agents']
    cameras = data['cameras']
    
    reverse_blueprint_mapping = create_reverse_blueprint_mapping()
    
    # 分类处理所有物体，添加命名计数
    room_objects = []
    personal_objects = []
    asset_type_counters = {}
    
    # 先确定标签位置和命名
    for i, obj in enumerate(objects):
        obj_type = get_object_display_type(obj)
        
        # 命名计数
        if obj_type in asset_type_counters:
            asset_type_counters[obj_type] += 1
            display_name = f"{obj_type}_{asset_type_counters[obj_type]}"
        else:
            asset_type_counters[obj_type] = 1
            display_name = f"{obj_type}_1"
        
        obj['display_name'] = display_name
    
    # 计算标签位置
    for i, obj in enumerate(objects):
        label_pos = determine_label_position(i, objects)
        obj['label_position'] = label_pos
    
    # 分类物体
    for obj in objects:
        owner = obj.get('owner', 'unknown')
        processed_obj = {
            'id': obj['id'],
            'type': get_object_display_type(obj),
            'position': obj['position'],
            'rotation': obj['rotation'],
            'owner': owner,
            'bounds': obj.get('aabb_bounds', None),
            'display_name': obj.get('display_name', ''),
            'label_position': obj.get('label_position', {'position': 'top', 'offset_y': -8})
        }
        
        if owner == 'room':
            room_objects.append(processed_obj)
        else:
            personal_objects.append(processed_obj)
    
    # 处理代理人标签位置
    agent_labels_data = []
    for agent in agents:
        agent_labels_data.append({
            'x': agent['position']['x'],
            'y': agent['position']['y'],
            'offset_y': -20
        })
    adjust_simple_label_position(agent_labels_data, min_distance=30)
    
    # 处理代理人
    processed_agents = []
    for i, agent in enumerate(agents):
        agent_type = agent['features']['type'] if 'features' in agent else 'unknown'
        
        processed_agent = {
            'id': agent['id'],
            'type': agent_type,
            'display_name': reverse_blueprint_mapping.get(agent_type, agent_type),
            'position': agent['position'],
            'rotation': agent['rotation'],
            'label_offset': agent_labels_data[i]['offset_y']
        }
        processed_agents.append(processed_agent)
    
    # 处理相机标签位置
    camera_labels_data = []
    for camera in cameras:
        camera_labels_data.append({
            'x': camera['position']['x'],
            'y': camera['position']['y'],
            'offset_y': 8
        })
    adjust_simple_label_position(camera_labels_data, min_distance=25)
    
    # 处理相机，添加方向向量（过滤掉TopCamera）
    processed_cameras = []
    for i, camera in enumerate(cameras):
        # 跳过TopCamera
        if 'TopCamera' in camera['id']:
            continue
            
        rot = camera['rotation']
        forward_x, forward_y, _ = quaternion_to_direction_vector(rot['x'], rot['y'], rot['z'], rot['w'])
        
        processed_camera = {
            'id': camera['id'],
            'position': camera['position'],
            'rotation': camera['rotation'],
            'direction': {'x': forward_x, 'y': forward_y},
            'display_name': f'Camera_{len(processed_cameras)+1}',
            'label_offset': camera_labels_data[i]['offset_y']
        }
        processed_cameras.append(processed_camera)
    
    return {
        'table': {
            'position': scene_info['position'],
            'rotation': scene_info['rotation'],
            'bounds': scene_info['aabb_bounds'],
        },
        'roomObjects': room_objects,
        'personalObjects': personal_objects,
        'agents': processed_agents,
        'cameras': processed_cameras
    }

def generate_visualization_html(scene_data):
    """生成可视化HTML内容"""
    processed_data = process_scene_data(scene_data)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Scene Visualization</title>
        <meta charset="utf-8">
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            #visualization {{
                width: 1000px;
                height: 800px;
                border: 1px solid #ccc;
                position: relative;
            }}
            .table {{ fill: #9E9E9E; opacity: 0.3; stroke: #9E9E9E; stroke-width: 2; }}
            .room-object {{ fill: #2196F3; }}
            .personal-object {{ fill: #4CAF50; }}
            .agent {{ fill: #FF9800; }}
            .camera {{ fill: #F44336; }}
            .object-bounds {{
                fill: none;
                stroke-width: 1;
                opacity: 0.5;
            }}
            .room-bounds {{ stroke: #2196F3; fill: #2196F3; fill-opacity: 0.15; }}
            .personal-bounds {{ 
                stroke: #4CAF50; 
                fill: #4CAF50; 
                fill-opacity: 0.02; 
                stroke-opacity: 0.3;
                stroke-width: 1;
                transition: all 0.3s ease;
            }}
            .personal-bounds.highlighted {{ 
                fill-opacity: 0.25; 
                stroke-opacity: 1.0;
                stroke-width: 2; 
            }}
            .personal-object {{ 
                fill-opacity: 0.4;
                transition: all 0.3s ease;
            }}
            .personal-object.highlighted {{ 
                fill-opacity: 1.0;
            }}
            .label {{
                font-size: 8px;
                font-weight: bold;
                pointer-events: none;
            }}
            .personal-label {{
                font-size: 6px;
                opacity: 0.6;
                transition: all 0.3s ease;
            }}
            .personal-label.highlighted {{
                font-size: 9px;
                opacity: 1.0;
            }}
            .label-bg {{
                fill: white;
                opacity: 0.8;
                transition: all 0.3s ease;
            }}
            .personal-label.highlighted + .label-bg {{
                opacity: 1.0;
            }}
            .direction-arrow {{
                stroke-width: 2;
                fill: none;
            }}
        </style>
    </head>
    <body>
        <h1>Scene Visualization</h1>
        <div id="visualization"></div>
        <script>
            const sceneData = {json.dumps(processed_data)};
            
            // 创建SVG
            const svg = d3.select("#visualization")
                .append("svg")
                .attr("width", "100%")
                .attr("height", "100%");
            
            // 定义箭头标记
            svg.append("defs").append("marker")
                .attr("id", "arrow")
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 10)
                .attr("refY", 0)
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M0,-5L10,0L0,5")
                .attr("fill", "#F44336");
            
            // 禁用缩放和平移功能（固定视图）
            const zoom = d3.zoom()
                .scaleExtent([1, 1])  // 禁用缩放，固定比例为1
                .on("zoom", null);     // 禁用所有缩放事件
            
            // 不调用svg.call(zoom)，完全禁用交互
            
            // 创建容器
            const container = svg.append("g");
            
            // 绘制表格边界
            container.append("rect")
                .attr("x", sceneData.table.bounds.min.x)
                .attr("y", sceneData.table.bounds.min.y)
                .attr("width", sceneData.table.bounds.max.x - sceneData.table.bounds.min.x)
                .attr("height", sceneData.table.bounds.max.y - sceneData.table.bounds.min.y)
                .attr("class", "table");
            
            // 绘制房间物体
            sceneData.roomObjects.forEach(obj => {{
                if (obj.bounds) {{
                    container.append("rect")
                        .attr("x", obj.bounds.min.x)
                        .attr("y", obj.bounds.min.y)
                        .attr("width", obj.bounds.max.x - obj.bounds.min.x)
                        .attr("height", obj.bounds.max.y - obj.bounds.min.y)
                        .attr("class", "object-bounds room-bounds");
                }}
                
                container.append("circle")
                    .attr("class", "room-object")
                    .attr("cx", obj.position.x)
                    .attr("cy", obj.position.y)
                    .attr("r", 5)
                    .attr("stroke", "black")
                    .attr("stroke-width", 0.5);
                
                // 添加标签
                if (obj.bounds) {{
                    const centerX = (obj.bounds.min.x + obj.bounds.max.x) / 2;
                    const anchorY = obj.label_position.position === 'top' ? obj.bounds.min.y : obj.bounds.max.y;
                    const offsetY = obj.label_position.offset_y;
                    
                    const labelGroup = container.append("g");
                    const text = labelGroup.append("text")
                        .attr("class", "label")
                        .attr("x", centerX)
                        .attr("y", anchorY + offsetY)
                        .attr("text-anchor", "middle")
                        .attr("fill", "#2196F3")
                        .text(obj.display_name);
                    
                    const bbox = text.node().getBBox();
                    labelGroup.insert("rect", "text")
                        .attr("class", "label-bg")
                        .attr("x", bbox.x - 2)
                        .attr("y", bbox.y - 1)
                        .attr("width", bbox.width + 4)
                        .attr("height", bbox.height + 2)
                        .attr("rx", 2);
                }}
            }});
            
            // 绘制个人物体（添加交互）
            sceneData.personalObjects.forEach((obj, index) => {{
                const objGroup = container.append("g")
                    .attr("class", "personal-obj-group")
                    .attr("data-index", index);
                
                if (obj.bounds) {{
                    objGroup.append("rect")
                        .attr("x", obj.bounds.min.x)
                        .attr("y", obj.bounds.min.y)
                        .attr("width", obj.bounds.max.x - obj.bounds.min.x)
                        .attr("height", obj.bounds.max.y - obj.bounds.min.y)
                        .attr("class", "object-bounds personal-bounds")
                        .style("cursor", "pointer")
                        .on("mouseenter", function() {{
                            d3.select(this).classed("highlighted", true);
                            objGroup.select(".personal-object").classed("highlighted", true);
                            objGroup.selectAll(".personal-label").classed("highlighted", true);
                        }})
                        .on("mouseleave", function() {{
                            d3.select(this).classed("highlighted", false);
                            objGroup.select(".personal-object").classed("highlighted", false);
                            objGroup.selectAll(".personal-label").classed("highlighted", false);
                        }});
                }}
                
                objGroup.append("circle")
                    .attr("class", "personal-object")
                    .attr("cx", obj.position.x)
                    .attr("cy", obj.position.y)
                    .attr("r", 3)
                    .attr("stroke", "black")
                    .attr("stroke-width", 0.5)
                    .style("cursor", "pointer")
                    .on("mouseenter", function() {{
                        d3.select(this)
                            .classed("highlighted", true)
                            .transition()
                            .duration(200)
                            .attr("r", 6);
                        objGroup.select(".personal-bounds").classed("highlighted", true);
                        objGroup.selectAll(".personal-label").classed("highlighted", true);
                    }})
                    .on("mouseleave", function() {{
                        d3.select(this)
                            .classed("highlighted", false)
                            .transition()
                            .duration(200)
                            .attr("r", 3);
                        objGroup.select(".personal-bounds").classed("highlighted", false);
                        objGroup.selectAll(".personal-label").classed("highlighted", false);
                    }});
                
                // 添加标签
                if (obj.bounds) {{
                    const centerX = (obj.bounds.min.x + obj.bounds.max.x) / 2;
                    const anchorY = obj.label_position.position === 'top' ? obj.bounds.min.y : obj.bounds.max.y;
                    const offsetY = obj.label_position.offset_y;
                    
                    const labelGroup = objGroup.append("g");
                    const text = labelGroup.append("text")
                        .attr("class", "label personal-label")
                        .attr("x", centerX)
                        .attr("y", anchorY + offsetY)
                        .attr("text-anchor", "middle")
                        .attr("fill", "#4CAF50")
                        .text(obj.display_name);
                    
                    const bbox = text.node().getBBox();
                    labelGroup.insert("rect", "text")
                        .attr("class", "label-bg")
                        .attr("x", bbox.x - 2)
                        .attr("y", bbox.y - 1)
                        .attr("width", bbox.width + 4)
                        .attr("height", bbox.height + 2)
                        .attr("rx", 2)
                        .style("opacity", 0.6)
                        .style("transition", "all 0.3s ease");
                }}
            }});
            
            // 绘制代理人（菱形，无箭头，标签在上方）
            sceneData.agents.forEach(agent => {{
                // 绘制菱形
                const size = 8;
                const path = `M ${{agent.position.x}},${{agent.position.y - size}} 
                             L ${{agent.position.x + size}},${{agent.position.y}} 
                             L ${{agent.position.x}},${{agent.position.y + size}} 
                             L ${{agent.position.x - size}},${{agent.position.y}} Z`;
                
                container.append("path")
                    .attr("d", path)
                    .attr("class", "agent")
                    .attr("stroke", "black")
                    .attr("stroke-width", 1.5);
                
                // 添加标签（放在上方）
                const labelGroup = container.append("g");
                const text = labelGroup.append("text")
                    .attr("class", "label")
                    .attr("x", agent.position.x)
                    .attr("y", agent.position.y - 15)
                    .attr("text-anchor", "middle")
                    .attr("fill", "#FF9800")
                    .text(agent.display_name);
                
                const bbox = text.node().getBBox();
                labelGroup.insert("rect", "text")
                    .attr("class", "label-bg")
                    .attr("x", bbox.x - 3)
                    .attr("y", bbox.y - 1)
                    .attr("width", bbox.width + 6)
                    .attr("height", bbox.height + 2)
                    .attr("rx", 3);
            }});
            
            // 绘制相机（三角形+箭头）
            sceneData.cameras.forEach(camera => {{
                // 绘制三角形
                const size = 6;
                const path = `M ${{camera.position.x}},${{camera.position.y - size}} 
                             L ${{camera.position.x - size}},${{camera.position.y + size}} 
                             L ${{camera.position.x + size}},${{camera.position.y + size}} Z`;
                
                container.append("path")
                    .attr("d", path)
                    .attr("class", "camera")
                    .attr("stroke", "black")
                    .attr("stroke-width", 1.5);
                
                // 绘制方向箭头
                const arrowLength = 20;
                const magnitude = Math.sqrt(camera.direction.x ** 2 + camera.direction.y ** 2);
                if (magnitude > 0) {{
                    const normX = camera.direction.x / magnitude;
                    const normY = camera.direction.y / magnitude;
                    const endX = camera.position.x + normX * arrowLength;
                    const endY = camera.position.y + normY * arrowLength;
                    
                    container.append("line")
                        .attr("x1", camera.position.x)
                        .attr("y1", camera.position.y)
                        .attr("x2", endX)
                        .attr("y2", endY)
                        .attr("class", "direction-arrow")
                        .attr("stroke", "#F44336")
                        .attr("marker-end", "url(#arrow)");
                }}
                
                // 添加标签
                const labelGroup = container.append("g");
                const text = labelGroup.append("text")
                    .attr("class", "label")
                    .attr("x", camera.position.x)
                    .attr("y", camera.position.y + camera.label_offset)
                    .attr("text-anchor", "middle")
                    .attr("fill", "#F44336")
                    .text(camera.display_name);
                
                const bbox = text.node().getBBox();
                labelGroup.insert("rect", "text")
                    .attr("class", "label-bg")
                    .attr("x", bbox.x - 2)
                    .attr("y", bbox.y - 1)
                    .attr("width", bbox.width + 4)
                    .attr("height", bbox.height + 2)
                    .attr("rx", 2);
            }});
            
            // 自动缩放以适应所有内容（只在初始化时设置，不可交互）
            const bounds = container.node().getBBox();
            const scale = Math.min(
                900 / bounds.width,
                700 / bounds.height
            );
            
            // 设置固定变换（不使用zoom，直接设置transform）
            container.attr("transform", 
                `translate(${500 - bounds.x * scale - bounds.width * scale / 2}, ${400 - bounds.y * scale - bounds.height * scale / 2}) scale(${scale})`
            );
        </script>
    </body>
    </html>
    """
    return html_content
