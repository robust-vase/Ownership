"""
场景平面图面板生成器
负责生成D3.js场景可视化图的HTML代码
"""
import json

def generate_scene_panel_html():
    """
    生成场景平面图面板的HTML框架
    
    Returns:
        HTML字符串
    """
    html = """
                <!-- 场景平面图区域 -->
                <div class="scene-panel">
                    <div class="panel-title">场景平面图</div>
                    <div id="scene-visualization"></div>
                </div>
    """
    
    return html


def generate_scene_visualization_script(processed_data):
    """
    生成场景可视化的JavaScript代码
    
    Args:
        processed_data: 处理后的场景数据
    
    Returns:
        JavaScript代码字符串
    """
    script = f"""
            // ==================== 场景平面图可视化 ====================
            const sceneData = {json.dumps(processed_data)};
            
            // 创建SVG
            const svg = d3.select("#scene-visualization")
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
            
            // 创建缩放功能（允许0.8-1.8倍缩放，以桌子中心为缩放中心）
            const zoom = d3.zoom()
                .scaleExtent([0.8, 1.8])  // 允许0.8到1.8倍缩放
                .on("zoom", (event) => {{
                    container.attr("transform", event.transform);
                }});
            
            svg.call(zoom);
            
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
                            // 动态调整白色底尺寸以适应放大的文字
                            setTimeout(() => {{
                                objGroup.selectAll(".personal-label").each(function() {{
                                    const labelNode = this;
                                    const bgNode = this.previousSibling;
                                    if (bgNode && bgNode.classList.contains('personal-label-bg')) {{
                                        const bbox = labelNode.getBBox();
                                        d3.select(bgNode)
                                            .attr('x', bbox.x - 2)
                                            .attr('y', bbox.y - 1)
                                            .attr('width', bbox.width + 4)
                                            .attr('height', bbox.height + 2);
                                    }}
                                }});
                            }}, 50);
                        }})
                        .on("mouseleave", function() {{
                            d3.select(this).classed("highlighted", false);
                            objGroup.select(".personal-object").classed("highlighted", false);
                            objGroup.selectAll(".personal-label").classed("highlighted", false);
                            // 动态调整白色底尺寸以适应缩小的文字
                            setTimeout(() => {{
                                objGroup.selectAll(".personal-label").each(function() {{
                                    const labelNode = this;
                                    const bgNode = this.previousSibling;
                                    if (bgNode && bgNode.classList.contains('personal-label-bg')) {{
                                        const bbox = labelNode.getBBox();
                                        d3.select(bgNode)
                                            .attr('x', bbox.x - 2)
                                            .attr('y', bbox.y - 1)
                                            .attr('width', bbox.width + 4)
                                            .attr('height', bbox.height + 2);
                                    }}
                                }});
                            }}, 50);
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
                        // 动态调整白色底尺寸
                        setTimeout(() => {{
                            objGroup.selectAll(".personal-label").each(function() {{
                                const labelNode = this;
                                const bgNode = this.previousSibling;
                                if (bgNode && bgNode.classList.contains('personal-label-bg')) {{
                                    const bbox = labelNode.getBBox();
                                    d3.select(bgNode)
                                        .attr('x', bbox.x - 2)
                                        .attr('y', bbox.y - 1)
                                        .attr('width', bbox.width + 4)
                                        .attr('height', bbox.height + 2);
                                }}
                            }});
                        }}, 50);
                    }})
                    .on("mouseleave", function() {{
                        d3.select(this)
                            .classed("highlighted", false)
                            .transition()
                            .duration(200)
                            .attr("r", 3);
                        objGroup.select(".personal-bounds").classed("highlighted", false);
                        objGroup.selectAll(".personal-label").classed("highlighted", false);
                        // 动态调整白色底尺寸
                        setTimeout(() => {{
                            objGroup.selectAll(".personal-label").each(function() {{
                                const labelNode = this;
                                const bgNode = this.previousSibling;
                                if (bgNode && bgNode.classList.contains('personal-label-bg')) {{
                                    const bbox = labelNode.getBBox();
                                    d3.select(bgNode)
                                        .attr('x', bbox.x - 2)
                                        .attr('y', bbox.y - 1)
                                        .attr('width', bbox.width + 4)
                                        .attr('height', bbox.height + 2);
                                }}
                            }});
                        }}, 50);
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
                        .attr("class", "label-bg personal-label-bg")
                        .attr("x", bbox.x - 2)
                        .attr("y", bbox.y - 1)
                        .attr("width", bbox.width + 4)
                        .attr("height", bbox.height + 2)
                        .attr("rx", 2);
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
            
            // 自动缩放以适应所有内容（刚好框住所有物品，留足够边距）
            const bounds = container.node().getBBox();
            const svgRect = svg.node().getBoundingClientRect();
            
            // 获取桌子中心坐标（从scene_info中获取）
            const tableCenter = {{
                x: sceneData.table.position.x,
                y: sceneData.table.position.y
            }};
            
            // 计算刚好合适的缩放比例（留85%的空间，留更多边距）
            const scale = Math.min(
                (svgRect.width * 0.85) / bounds.width,
                (svgRect.height * 0.85) / bounds.height
            );
            
            // 计算以桌子中心为基准的translate值
            const translateX = svgRect.width / 2 - tableCenter.x * scale;
            const translateY = svgRect.height / 2 - tableCenter.y * scale;
            
            // 设置初始变换，以桌子中心居中显示
            const initialTransform = d3.zoomIdentity
                .translate(translateX, translateY)
                .scale(scale);
            
            // 应用初始变换
            svg.call(zoom.transform, initialTransform);
            
            // 配置zoom，使缩放以桌子中心为基准（禁用平移）
            zoom.on("zoom", (event) => {{
                const transform = event.transform;
                // 计算新的translate，使缩放始终以桌子中心为基准
                const newTranslateX = svgRect.width / 2 - tableCenter.x * transform.k;
                const newTranslateY = svgRect.height / 2 - tableCenter.y * transform.k;
                
                container.attr("transform", 
                    `translate(${{newTranslateX}}, ${{newTranslateY}}) scale(${{transform.k}})`
                );
            }});
    """
    
    return script


def generate_scene_interaction_script():
    """
    生成场景交互逻辑的JavaScript代码
    
    Returns:
        JavaScript代码字符串
    """
    script = """
            // ==================== 交互联动 ====================
            // 存储当前点击的物体ID
            let currentClickedObjectId = null;
            
            // 高亮指定物体（点击状态）
            function highlightObject(objectId) {
                // 取消之前的高亮
                if (currentClickedObjectId) {
                    unhighlightObject(currentClickedObjectId);
                }
                
                currentClickedObjectId = objectId;
                
                // 高亮所有相机中的该物体bbox
                document.querySelectorAll(`[data-object-id="${objectId}"]`).forEach(group => {
                    const rect = group.querySelector('.bbox-rect');
                    const label = group.querySelector('.bbox-label');
                    const labelBg = group.querySelector('.bbox-label-bg');
                    if (rect) rect.classList.add('highlighted');
                    if (label && labelBg) {
                        // 先添加class
                        label.classList.add('highlighted');
                        labelBg.classList.add('highlighted');
                        
                        // 等待CSS transition完成（300ms）+ 额外缓冲时间，然后调整背景尺寸
                        setTimeout(() => {
                            try {
                                const bbox = label.getBBox();
                                labelBg.setAttribute('x', bbox.x - 3);
                                labelBg.setAttribute('y', bbox.y - 2);
                                labelBg.setAttribute('width', bbox.width + 6);
                                labelBg.setAttribute('height', bbox.height + 4);
                            } catch (e) {
                                console.error('getBBox error:', e);
                            }
                        }, 350);  // 增加到350ms，确保transition完成
                    }
                });
                
                // 高亮平面图中的物体
                container.selectAll('.personal-obj-group').each(function(d, i) {
                    const group = d3.select(this);
                    const objId = sceneData.personalObjects[i].id;
                    if (objId === objectId) {
                        group.select('.personal-bounds').classed('clicked', true);
                        group.select('.personal-object')
                            .classed('clicked', true)
                            .transition()
                            .duration(200)
                            .attr('r', 6);
                        const labels = group.selectAll('.personal-label').classed('clicked', true);
                        
                        // 动态调整平面图标签背景
                        setTimeout(() => {
                            group.selectAll('.personal-label').each(function() {
                                const labelNode = this;
                                const bgNode = this.previousSibling;
                                if (bgNode && bgNode.classList.contains('personal-label-bg')) {
                                    try {
                                        const bbox = labelNode.getBBox();
                                        d3.select(bgNode)
                                            .attr('x', bbox.x - 2)
                                            .attr('y', bbox.y - 1)
                                            .attr('width', bbox.width + 4)
                                            .attr('height', bbox.height + 2);
                                    } catch (e) {}
                                }
                            });
                        }, 50);
                    }
                });
            }
            
            // 取消高亮
            function unhighlightObject(objectId) {
                // 取消相机bbox高亮
                document.querySelectorAll(`[data-object-id="${objectId}"]`).forEach(group => {
                    const rect = group.querySelector('.bbox-rect');
                    const label = group.querySelector('.bbox-label');
                    const labelBg = group.querySelector('.bbox-label-bg');
                    if (rect) rect.classList.remove('highlighted');
                    if (label) {
                        label.classList.remove('highlighted');
                        // 先移除class让文字缩小，然后调整背景尺寸以适应缩小的文字
                        if (labelBg) {
                            labelBg.classList.remove('highlighted');
                            setTimeout(() => {
                                try {
                                    const bbox = label.getBBox();
                                    labelBg.setAttribute('x', bbox.x - 3);
                                    labelBg.setAttribute('y', bbox.y - 2);
                                    labelBg.setAttribute('width', bbox.width + 6);
                                    labelBg.setAttribute('height', bbox.height + 4);
                                } catch (e) {}
                            }, 50);
                        }
                    }
                });
                
                // 取消平面图高亮
                container.selectAll('.personal-obj-group').each(function(d, i) {
                    const group = d3.select(this);
                    const objId = sceneData.personalObjects[i].id;
                    if (objId === objectId) {
                        group.select('.personal-bounds').classed('clicked', false);
                        group.select('.personal-object')
                            .classed('clicked', false)
                            .transition()
                            .duration(200)
                            .attr('r', 3);
                        group.selectAll('.personal-label').classed('clicked', false);
                        
                        // 调整平面图标签背景
                        setTimeout(() => {
                            group.selectAll('.personal-label').each(function() {
                                const labelNode = this;
                                const bgNode = this.previousSibling;
                                if (bgNode && bgNode.classList.contains('personal-label-bg')) {
                                    try {
                                        const bbox = labelNode.getBBox();
                                        d3.select(bgNode)
                                            .attr('x', bbox.x - 2)
                                            .attr('y', bbox.y - 1)
                                            .attr('width', bbox.width + 4)
                                            .attr('height', bbox.height + 2);
                                    } catch (e) {}
                                }
                            });
                        }, 50);
                    }
                });
                
                if (currentClickedObjectId === objectId) {
                    currentClickedObjectId = null;
                }
            }
            
            // 为平面图中的个人物体添加点击交互
            sceneData.personalObjects.forEach((obj, index) => {
                const groups = container.selectAll(`.personal-obj-group[data-index="${index}"]`);
                
                groups.on('click', function(event) {
                    event.stopPropagation();
                    if (currentClickedObjectId === obj.id) {
                        // 如果已经点击，则取消
                        unhighlightObject(obj.id);
                    } else {
                        // 否则高亮该物体
                        highlightObject(obj.id);
                    }
                });
                
                // 保持hover效果
                groups.select('.personal-bounds')
                    .on('mouseenter', function() {
                        if (currentClickedObjectId !== obj.id) {
                            d3.select(this).classed('highlighted', true);
                        }
                    })
                    .on('mouseleave', function() {
                        if (currentClickedObjectId !== obj.id) {
                            d3.select(this).classed('highlighted', false);
                        }
                    });
                
                groups.select('.personal-object')
                    .on('mouseenter', function() {
                        if (currentClickedObjectId !== obj.id) {
                            d3.select(this).classed('highlighted', true);
                        }
                    })
                    .on('mouseleave', function() {
                        if (currentClickedObjectId !== obj.id) {
                            d3.select(this).classed('highlighted', false);
                        }
                    });
            });
            
            // 点击空白区域取消选择
            svg.on('click', function(event) {
                if (event.target === this || event.target.tagName === 'rect' && event.target.classList.contains('table')) {
                    if (currentClickedObjectId) {
                        unhighlightObject(currentClickedObjectId);
                    }
                }
            });
            
            // ==================== bbox交互设置 ====================
            function setupBboxInteractions() {
                document.querySelectorAll('.bbox-group').forEach(group => {
                    const objectId = group.getAttribute('data-object-id');
                    
                    // 点击事件
                    group.addEventListener('click', function(event) {
                        event.stopPropagation();
                        if (currentClickedObjectId === objectId) {
                            unhighlightObject(objectId);
                        } else {
                            highlightObject(objectId);
                        }
                    });
                    
                    // Hover效果
                    group.addEventListener('mouseenter', function() {
                        if (currentClickedObjectId !== objectId) {
                            const rect = this.querySelector('.bbox-rect');
                            const label = this.querySelector('.bbox-label');
                            const labelBg = this.querySelector('.bbox-label-bg');
                            if (rect) rect.classList.add('highlighted');
                            if (label) label.classList.add('highlighted');
                            if (labelBg) labelBg.classList.add('highlighted');
                        }
                    });
                    
                    group.addEventListener('mouseleave', function() {
                        if (currentClickedObjectId !== objectId) {
                            const rect = this.querySelector('.bbox-rect');
                            const label = this.querySelector('.bbox-label');
                            const labelBg = this.querySelector('.bbox-label-bg');
                            if (rect) rect.classList.remove('highlighted');
                            if (label) label.classList.remove('highlighted');
                            if (labelBg) labelBg.classList.remove('highlighted');
                        }
                    });
                });
            }
    """
    
    return script
