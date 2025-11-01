"""
TopCamera匹配区域面板生成器
负责生成TopCamera图片、物品bbox和人物标签的HTML代码
"""

def generate_topcamera_panel_html(topcamera_images, images_relative_path):
    """
    生成TopCamera匹配区域面板的HTML内容
    
    Args:
        topcamera_images: TopCamera图片文件列表
        images_relative_path: 图片相对路径
    
    Returns:
        HTML字符串
    """
    html = """
                <!-- 匹配区域 -->
                <div class="match-panel" style="position: relative;">
                    <div class="panel-title">匹配区域 (TopCamera)</div>
                    
                    <div style="display: flex; gap: 15px; height: calc(100% - 60px);">
                        <!-- 左侧：人物标签区域 (20% 宽度) -->
                        <div class="agent-tags-container" id="agent-tags-container" style="width: 20%; overflow-y: auto;">
                            <!-- 人物标签将通过JavaScript动态生成 -->
                        </div>
                        
                        <!-- 右侧：TopCamera图片 (80% 宽度) -->
                        <div class="topcamera-image-container" style="width: 80%; position: relative;">
    """
    
    if topcamera_images:
        image_name = topcamera_images[0].name
        html += f"""
                        <div class="image-wrapper" style="width: 100%; height: 100%;">
                            <img src="{images_relative_path}/{image_name}" 
                                 alt="TopCamera" 
                                 class="match-image" 
                                 id="topcamera-img"
                                 style="width: 100%; height: auto; display: block;">
                            <svg class="bbox-overlay" id="bbox-svg-topcamera"></svg>
                        </div>
        """
    else:
        html += """
                        <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #999;">
                            <p>No TopCamera image available</p>
                        </div>
        """
    
    html += """
                        </div>
                    </div>
                </div>
    """
    
    return html


def generate_topcamera_script(image_width=4096, image_height=4096):
    """
    生成TopCamera绘制和交互的JavaScript代码
    
    Args:
        image_width: 图片宽度
        image_height: 图片高度
    
    Returns:
        JavaScript代码字符串
    """
    script = f"""
            // ==================== TopCamera专门绘制（包含人物标签） ====================
            // 存储物品与人物的关系
            const objectOwnershipMap = {{}};
            
            // 定义人物颜色映射（除了绿色，使用显眼的颜色）
            const agentColors = [
                '#FF5722',  // 深橙色
                '#2196F3',  // 蓝色
                '#9C27B0',  // 紫色
                '#FF9800',  // 橙色
                '#E91E63',  // 粉红色
                '#00BCD4',  // 青色
                '#FFEB3B',  // 黄色
                '#795548'   // 棕色
            ];
            
            // 生成左侧人物标签
            function generateAgentTags() {{
                const container = document.getElementById('agent-tags-container');
                if (!container || !projections.topcamera_agents) return;
                
                container.innerHTML = '';
                
                // 添加公共和未知标签
                const specialTags = [
                    {{ id: 'public', name: 'Public', color: '#9E9E9E' }},
                    {{ id: 'unknown', name: 'Unknown', color: '#607D8B' }}
                ];
                
                specialTags.forEach(tag => {{
                    createAgentTagWithObjects(container, tag.id, tag.name, tag.color);
                }});
                
                // 添加普通人物标签
                const agents = Object.entries(projections.topcamera_agents);
                agents.forEach(([agentId, agentData], index) => {{
                    const color = agentColors[index % agentColors.length];
                    createAgentTagWithObjects(container, agentId, agentData.display_name, color);
                }});
                
                // 添加按钮容器
                const buttonContainer = document.createElement('div');
                buttonContainer.style.cssText = 'display: flex; gap: 10px; margin-top: auto; padding-top: 15px;';
                
                // 提交按钮
                const submitBtn = document.createElement('button');
                submitBtn.textContent = '提交';
                submitBtn.style.cssText = 'flex: 1; padding: 10px; background: #4CAF50; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px;';
                submitBtn.onclick = submitAllOwnerships;
                
                // 重置按钮
                const resetBtn = document.createElement('button');
                resetBtn.textContent = '重置';
                resetBtn.style.cssText = 'flex: 1; padding: 10px; background: #F44336; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px;';
                resetBtn.onclick = resetAllOwnerships;
                
                buttonContainer.appendChild(submitBtn);
                buttonContainer.appendChild(resetBtn);
                container.appendChild(buttonContainer);
            }}
            
            // 创建单个人物标签及其物品列表
            function createAgentTagWithObjects(container, agentId, agentName, color) {{
                // 创建人物标签外层容器
                const agentContainer = document.createElement('div');
                agentContainer.style.cssText = 'display: flex; flex-direction: column; gap: 5px;';
                agentContainer.setAttribute('data-agent-container', agentId);
                
                // 人物标签框
                const tagBox = document.createElement('div');
                tagBox.className = 'agent-tag-box';
                tagBox.style.backgroundColor = color;
                tagBox.style.borderColor = color;
                tagBox.setAttribute('data-agent-id', agentId);
                tagBox.setAttribute('data-agent-name', agentName);
                tagBox.setAttribute('data-agent-color', color);
                tagBox.textContent = agentName;
                
                agentContainer.appendChild(tagBox);
                
                // 物品列表容器（虚线框）
                const objectsContainer = document.createElement('div');
                objectsContainer.className = 'agent-objects-container';
                objectsContainer.setAttribute('data-owner-id', agentId);
                objectsContainer.style.cssText = `
                    border: 2px dashed ${{color}};
                    border-radius: 5px;
                    padding: 5px;
                    min-height: 30px;
                    display: none;
                    flex-direction: column;
                    gap: 5px;
                    background-color: rgba(255, 255, 255, 0.5);
                `;
                
                agentContainer.appendChild(objectsContainer);
                container.appendChild(agentContainer);
            }}
            
            // 添加物品到人物标签下方
            function addObjectToAgentTag(agentId, objectId, objectName, agentColor) {{
                const objectsContainer = document.querySelector(`.agent-objects-container[data-owner-id="${{agentId}}"]`);
                if (!objectsContainer) return;
                
                // 显示容器
                objectsContainer.style.display = 'flex';
                
                // 创建物品框
                const objectBox = document.createElement('div');
                objectBox.className = 'agent-object-item';
                objectBox.setAttribute('data-object-id', objectId);
                objectBox.style.cssText = `
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 5px 8px;
                    background-color: white;
                    border: 1px solid ${{agentColor}};
                    border-radius: 4px;
                    font-size: 11px;
                    gap: 5px;
                `;
                
                // 物品名称
                const objectLabel = document.createElement('span');
                objectLabel.textContent = objectName;
                objectLabel.style.cssText = 'flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #333;';
                
                // 删除按钮
                const deleteBtn = document.createElement('button');
                deleteBtn.innerHTML = '❌';
                deleteBtn.style.cssText = `
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-size: 12px;
                    padding: 0;
                    width: 16px;
                    height: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    opacity: 0.7;
                    transition: opacity 0.2s;
                `;
                deleteBtn.onmouseover = () => deleteBtn.style.opacity = '1';
                deleteBtn.onmouseout = () => deleteBtn.style.opacity = '0.7';
                deleteBtn.onclick = (e) => {{
                    e.stopPropagation();
                    removeObjectOwnership(objectId, agentId);
                }};
                
                objectBox.appendChild(objectLabel);
                objectBox.appendChild(deleteBtn);
                objectsContainer.appendChild(objectBox);
            }}
            
            // 从人物标签移除物品
            function removeObjectFromAgentTag(agentId, objectId) {{
                const objectsContainer = document.querySelector(`.agent-objects-container[data-owner-id="${{agentId}}"]`);
                if (!objectsContainer) return;
                
                const objectBox = objectsContainer.querySelector(`.agent-object-item[data-object-id="${{objectId}}"]`);
                if (objectBox) {{
                    objectBox.remove();
                }}
                
                // 如果没有物品了，隐藏容器
                const remainingItems = objectsContainer.querySelectorAll('.agent-object-item');
                if (remainingItems.length === 0) {{
                    objectsContainer.style.display = 'none';
                }}
            }}
            
            // 移除单个物品的归属关系
            function removeObjectOwnership(objectId, agentId) {{
                // 从映射中删除
                if (objectOwnershipMap[objectId]) {{
                    delete objectOwnershipMap[objectId];
                    console.log('[DEBUG] Removed ownership:', objectId);
                }}
                
                // 从UI移除
                removeObjectFromAgentTag(agentId, objectId);
                
                // 恢复TopCamera中的bbox显示
                const bboxGroup = document.querySelector(`#bbox-svg-topcamera .bbox-group[data-object-id="${{objectId}}"]`);
                if (bboxGroup) {{
                    bboxGroup.style.display = '';
                    
                    // 恢复到原始位置
                    const rect = bboxGroup.querySelector('.bbox-rect');
                    const originalX = parseFloat(bboxGroup.getAttribute('data-original-x'));
                    const originalY = parseFloat(bboxGroup.getAttribute('data-original-y'));
                    
                    rect.setAttribute('x', originalX);
                    rect.setAttribute('y', originalY);
                    
                    const width = parseFloat(rect.getAttribute('width'));
                    const centerX = originalX + width / 2;
                    const labelY = originalY - 5;
                    
                    const label = bboxGroup.querySelector('.bbox-label');
                    const labelBg = bboxGroup.querySelector('.bbox-label-bg');
                    
                    label.setAttribute('x', centerX);
                    label.setAttribute('y', labelY);
                    
                    setTimeout(() => {{
                        try {{
                            const bbox = label.getBBox();
                            labelBg.setAttribute('x', bbox.x - 3);
                            labelBg.setAttribute('y', bbox.y - 2);
                        }} catch (e) {{}}
                    }}, 10);
                }}
                
                // 取消高亮
                unhighlightObject(objectId);
                
                console.log(`[INFO] Object ${{objectId}} ownership removed, bbox restored`);
            }}
            
            function drawTopCamera() {{
                if (!projections.topcamera) return;
                
                const svgElement = document.getElementById('bbox-svg-topcamera');
                const imgElement = document.getElementById('topcamera-img');
                
                if (!svgElement || !imgElement) return;
                
                if (!imgElement.complete) {{
                    imgElement.onload = () => drawTopCamera();
                    return;
                }}
                
                const displayWidth = imgElement.clientWidth;
                const displayHeight = imgElement.clientHeight;
                const scaleX = displayWidth / {image_width};
                const scaleY = displayHeight / {image_height};
                
                svgElement.setAttribute('viewBox', `0 0 ${{displayWidth}} ${{displayHeight}}`);
                svgElement.innerHTML = '';
                
                // 1. 绘制图片上的人物标签（使用左侧对应的颜色）
                if (projections.topcamera_agents) {{
                    const agents = Object.entries(projections.topcamera_agents);
                    agents.forEach(([agentId, agentData], index) => {{
                        if (!agentData.visible) return;
                        
                        const color = agentColors[index % agentColors.length];
                        const agentX = agentData.pixel_coords[0] * scaleX;
                        const agentY = agentData.pixel_coords[1] * scaleY;
                        const agentSize = 15;  // 正方形大小
                        
                        const agentGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                        agentGroup.setAttribute('class', 'agent-group');
                        agentGroup.setAttribute('data-agent-name', agentData.display_name);
                        agentGroup.setAttribute('style', 'pointer-events: none;');  // 不干扰拖动
                        
                        // 绘制彩色正方形（与左侧标签颜色一致）
                        const square = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                        square.setAttribute('x', agentX - agentSize/2);
                        square.setAttribute('y', agentY - agentSize/2);
                        square.setAttribute('width', agentSize);
                        square.setAttribute('height', agentSize);
                        square.setAttribute('fill', color);
                        square.setAttribute('stroke', 'black');
                        square.setAttribute('stroke-width', '1.5');
                        square.setAttribute('class', 'agent-marker');
                        
                        agentGroup.appendChild(square);
                        
                        // 人物标签
                        const agentLabelBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                        agentLabelBg.setAttribute('class', 'agent-label-bg');
                        agentLabelBg.setAttribute('fill', 'white');
                        agentLabelBg.setAttribute('opacity', '0.9');
                        agentLabelBg.setAttribute('rx', 2);
                        
                        const agentLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        agentLabel.setAttribute('x', agentX);
                        agentLabel.setAttribute('y', agentY - agentSize/2 - 5);
                        agentLabel.setAttribute('text-anchor', 'middle');
                        agentLabel.setAttribute('dominant-baseline', 'bottom');
                        agentLabel.setAttribute('fill', color);
                        agentLabel.setAttribute('font-size', '8px');
                        agentLabel.setAttribute('font-weight', 'bold');
                        agentLabel.textContent = agentData.display_name;
                        
                        agentGroup.appendChild(agentLabelBg);
                        agentGroup.appendChild(agentLabel);
                        svgElement.appendChild(agentGroup);
                        
                        // 更新标签背景
                        setTimeout(() => {{
                            try {{
                                const bbox = agentLabel.getBBox();
                                agentLabelBg.setAttribute('x', bbox.x - 3);
                                agentLabelBg.setAttribute('y', bbox.y - 2);
                                agentLabelBg.setAttribute('width', bbox.width + 6);
                                agentLabelBg.setAttribute('height', bbox.height + 4);
                            }} catch (e) {{}}
                        }}, 10);
                    }});
                }}
                
                // 2. 绘制物品bbox（只显示未归属的个人物品）
                Object.entries(projections.topcamera).forEach(([objectId, projection]) => {{
                    if (projection.owner === 'room' || !projection.visible) return;
                    if (objectOwnershipMap[objectId]) return;  // 已归属的不显示
                    
                    const [xMin, yMin, xMax, yMax] = projection.bbox;
                    const x = xMin * scaleX;
                    const y = yMin * scaleY;
                    const width = (xMax - xMin) * scaleX;
                    const height = (yMax - yMin) * scaleY;
                    
                    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                    g.setAttribute('class', 'bbox-group');
                    g.setAttribute('data-object-id', objectId);
                    g.setAttribute('data-original-x', x);
                    g.setAttribute('data-original-y', y);
                    
                    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    rect.setAttribute('x', x);
                    rect.setAttribute('y', y);
                    rect.setAttribute('width', width);
                    rect.setAttribute('height', height);
                    rect.setAttribute('class', 'bbox-rect');
                    
                    g.appendChild(rect);
                    
                    const centerX = x + width / 2;
                    const labelY = y - 5;
                    
                    const textBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    textBg.setAttribute('class', 'bbox-label-bg');
                    textBg.setAttribute('rx', 2);
                    
                    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    text.setAttribute('x', centerX);
                    text.setAttribute('y', labelY);
                    text.setAttribute('text-anchor', 'middle');
                    text.setAttribute('dominant-baseline', 'bottom');
                    text.setAttribute('class', 'bbox-label');
                    text.textContent = projection.display_name;
                    
                    g.appendChild(textBg);
                    g.appendChild(text);
                    svgElement.appendChild(g);
                    
                    setTimeout(() => {{
                        try {{
                            const bbox = text.getBBox();
                            textBg.setAttribute('x', bbox.x - 3);
                            textBg.setAttribute('y', bbox.y - 2);
                            textBg.setAttribute('width', bbox.width + 6);
                            textBg.setAttribute('height', bbox.height + 4);
                        }} catch (e) {{}}
                    }}, 10);
                }});
                
                // 绘制完成后，设置交互（拖动+点击高亮）
                setTimeout(() => {{
                    setupTopCameraDrag();
                    if (typeof setupBboxInteractions === 'function') {{
                        setupBboxInteractions();  // 重新绑定所有bbox的点击事件
                    }}
                }}, 50);
            }}
            
            // 先生成人物标签，再绘制图片
            generateAgentTags();
            
            // 图片加载完成后再绘制
            const topcameraImg = document.getElementById('topcamera-img');
            if (topcameraImg) {{
                if (topcameraImg.complete) {{
                    drawTopCamera();
                }} else {{
                    topcameraImg.onload = () => drawTopCamera();
                }}
            }}
            
            // ==================== TopCamera bbox拖动和关系存储 ====================
            // 全局变量存储拖动状态
            let draggedGroup = null;
            let isDragging = false;
            let offsetX = 0;
            let offsetY = 0;
            let currentHoveredAgent = null;
            
            // 鼠标移动处理函数（需要在外部定义，以便移除事件监听器）
            function handleTopCameraMouseMove(event) {{
                if (!draggedGroup || !isDragging) return;
                
                event.preventDefault();
                
                const topcameraSvg = document.getElementById('bbox-svg-topcamera');
                if (!topcameraSvg) return;
                
                const rect = draggedGroup.querySelector('.bbox-rect');
                const text = draggedGroup.querySelector('.bbox-label');
                const textBg = draggedGroup.querySelector('.bbox-label-bg');
                
                // 获取SVG边界
                const svgRect = topcameraSvg.getBoundingClientRect();
                
                // 计算SVG坐标系中鼠标的位置
                const mouseXinSVG = (event.clientX - svgRect.left) * (topcameraSvg.viewBox.baseVal.width / svgRect.width);
                const mouseYinSVG = (event.clientY - svgRect.top) * (topcameraSvg.viewBox.baseVal.height / svgRect.height);
                
                // 计算新位置（减去偏移，使鼠标位置保持在点击处）
                const newX = mouseXinSVG - offsetX;
                const newY = mouseYinSVG - offsetY;
                
                // 更新矩形位置
                rect.setAttribute('x', newX);
                rect.setAttribute('y', newY);
                
                // 更新标签位置
                const width = parseFloat(rect.getAttribute('width'));
                const centerX = newX + width / 2;
                const labelY = newY - 5;
                
                text.setAttribute('x', centerX);
                text.setAttribute('y', labelY);
                
                // 更新标签背景位置
                try {{
                    const bbox = text.getBBox();
                    textBg.setAttribute('x', bbox.x - 3);
                    textBg.setAttribute('y', bbox.y - 2);
                }} catch (e) {{}}
                
                // 检测鼠标是否在左侧人物标签框上
                currentHoveredAgent = null;
                const agentTags = document.querySelectorAll('.agent-tag-box');
                agentTags.forEach(tagBox => {{
                    const tagRect = tagBox.getBoundingClientRect();
                    
                    // 检测鼠标位置是否在标签框内
                    if (event.clientX >= tagRect.left && 
                        event.clientX <= tagRect.right && 
                        event.clientY >= tagRect.top && 
                        event.clientY <= tagRect.bottom) {{
                        
                        currentHoveredAgent = tagBox.getAttribute('data-agent-name');
                        tagBox.classList.add('highlight');
                    }} else {{
                        tagBox.classList.remove('highlight');
                    }}
                }});
            }}
            
            // 鼠标释放处理函数
            function handleTopCameraMouseUp(event) {{
                if (draggedGroup && isDragging) {{
                    const objectId = draggedGroup.getAttribute('data-object-id');
                    const text = draggedGroup.querySelector('.bbox-label');
                    
                    // 如果松开时在人物标签框上，存储关系并隐藏bbox
                    if (currentHoveredAgent) {{
                        const objectName = text.textContent;
                        
                        // 获取owner_id和color（从标签框的data属性）
                        const hoveredTagBox = document.querySelector(`.agent-tag-box[data-agent-name="${{currentHoveredAgent}}"]`);
                        const ownerId = hoveredTagBox ? hoveredTagBox.getAttribute('data-agent-id') : currentHoveredAgent;
                        const agentColor = hoveredTagBox ? hoveredTagBox.getAttribute('data-agent-color') : '#4CAF50';
                        
                        // 存储关系（只存储在内存中，点击提交时统一保存）
                        objectOwnershipMap[objectId] = {{
                            owner_name: currentHoveredAgent,
                            owner_id: ownerId,
                            object_name: objectName
                        }};
                        
                        console.log('[DEBUG] Ownership mapped:', objectId, '->', currentHoveredAgent, '(ID:', ownerId, ')');
                        
                        // 添加物品到人物标签下方的列表
                        addObjectToAgentTag(ownerId, objectId, objectName, agentColor);
                        
                        // 隐藏TopCamera中的bbox
                        draggedGroup.style.display = 'none';
                        
                        // 取消高亮状态
                        unhighlightObject(objectId);
                        
                        console.log(`物品 ${{objectName}} (ID: ${{objectId}}) 归属于 ${{currentHoveredAgent}} (ID: ${{ownerId}})`);
                    }} else {{
                        // 如果不在人物标签框上，恢复到原始位置
                        const rect = draggedGroup.querySelector('.bbox-rect');
                        const originalPosX = parseFloat(draggedGroup.getAttribute('data-original-x'));
                        const originalPosY = parseFloat(draggedGroup.getAttribute('data-original-y'));
                        
                        rect.setAttribute('x', originalPosX);
                        rect.setAttribute('y', originalPosY);
                        
                        const width = parseFloat(rect.getAttribute('width'));
                        const centerX = originalPosX + width / 2;
                        const labelY = originalPosY - 5;
                        
                        const label = draggedGroup.querySelector('.bbox-label');
                        const labelBg = draggedGroup.querySelector('.bbox-label-bg');
                        
                        label.setAttribute('x', centerX);
                        label.setAttribute('y', labelY);
                        
                        setTimeout(() => {{
                            try {{
                                const bbox = label.getBBox();
                                labelBg.setAttribute('x', bbox.x - 3);
                                labelBg.setAttribute('y', bbox.y - 2);
                            }} catch (e) {{}}
                        }}, 10);
                    }}
                    
                    draggedGroup.classList.remove('dragging');
                    draggedGroup = null;
                    isDragging = false;
                    currentHoveredAgent = null;
                    
                    // 移除所有高亮
                    document.querySelectorAll('.agent-tag-box').forEach(box => {{
                        box.classList.remove('highlight');
                    }});
                }}
            }}
            
            function setupTopCameraDrag() {{
                const topcameraSvg = document.getElementById('bbox-svg-topcamera');
                const topcameraContainer = document.querySelector('.topcamera-image-container');
                if (!topcameraSvg || !topcameraContainer) return;
                
                // 先移除旧的document级别事件监听器（避免重复绑定）
                document.removeEventListener('mousemove', handleTopCameraMouseMove);
                document.removeEventListener('mouseup', handleTopCameraMouseUp);
                
                // 添加新的document级别事件监听器
                document.addEventListener('mousemove', handleTopCameraMouseMove);
                document.addEventListener('mouseup', handleTopCameraMouseUp);
                
                topcameraSvg.querySelectorAll('.bbox-group').forEach(group => {{
                    const rect = group.querySelector('.bbox-rect');
                    const objectId = group.getAttribute('data-object-id');
                    if (!rect) return;
                    
                    // 鼠标按下事件
                    group.addEventListener('mousedown', function(event) {{
                        event.preventDefault();
                        event.stopPropagation();
                        
                        isDragging = true;
                        draggedGroup = group;
                        group.classList.add('dragging');
                        
                        // 计算鼠标相对于rect左上角的偏移
                        const svgRect = topcameraSvg.getBoundingClientRect();
                        const rectX = parseFloat(rect.getAttribute('x'));
                        const rectY = parseFloat(rect.getAttribute('y'));
                        
                        // SVG坐标系中鼠标的位置
                        const mouseXinSVG = (event.clientX - svgRect.left) * (topcameraSvg.viewBox.baseVal.width / svgRect.width);
                        const mouseYinSVG = (event.clientY - svgRect.top) * (topcameraSvg.viewBox.baseVal.height / svgRect.height);
                        
                        offsetX = mouseXinSVG - rectX;
                        offsetY = mouseYinSVG - rectY;
                    }});
                }});
            }}
            
            // Note: Individual save removed, only batch save on Submit

            
            // Submit all relationships
            function submitAllOwnerships() {{
                if (Object.keys(objectOwnershipMap).length === 0) {{
                    alert('No matching relationships to submit!');
                    return;
                }}
                
                // Build complete relationships list
                const allOwnerships = Object.entries(objectOwnershipMap).map(([objectId, ownerData]) => ({{
                    object_id: objectId,
                    object_name: ownerData.object_name,
                    owner_id: ownerData.owner_id,
                    owner_name: ownerData.owner_name,
                    timestamp: new Date().toISOString()
                }}));
                
                const sessionId = new Date().toISOString().replace(/[:.]/g, '-');
                
                console.log('[DEBUG] Submitting ownerships:', allOwnerships);
                console.log('[DEBUG] Session ID:', sessionId);
                console.log('[DEBUG] Current scene:', currentSceneName);
                
                // Send to server for batch saving (calls Python ownership_manager.py)
                fetch('/save_all_ownerships', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{ 
                        ownerships: allOwnerships,
                        session_id: sessionId,
                        scene_name: currentSceneName
                    }})
                }})
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error(`Server returned ${{response.status}}`);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    console.log('[SUCCESS] Server response:', data);
                    
                    // Show success message with auto-load option
                    const message = `Successfully submitted ${{allOwnerships.length}} matching relationships!\\nSession ID: ${{sessionId}}\\n\\nDo you want to load the next scene?`;
                    if (confirm(message)) {{
                        loadNextScene();
                    }}
                }})
                .catch(error => {{
                    console.error('[ERROR] Failed to submit to server:', error);
                    
                    // Save to local file as backup when server is unavailable
                    const batchData = {{
                        session_id: sessionId,
                        timestamp: new Date().toISOString(),
                        total_count: allOwnerships.length,
                        scene_name: currentSceneName,
                        ownerships: allOwnerships
                    }};
                    
                    // Create downloadable JSON file
                    const dataStr = JSON.stringify(batchData, null, 2);
                    const dataBlob = new Blob([dataStr], {{ type: 'application/json' }});
                    const url = URL.createObjectURL(dataBlob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `ownership_batch_${{sessionId}}.json`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                    
                    // Also save to localStorage as backup
                    localStorage.setItem('all_ownerships', JSON.stringify(batchData));
                    
                    console.log('[INFO] File saved locally:', `ownership_batch_${{sessionId}}.json`);
                    alert(`Server unavailable!\\n\\nSaved ${{allOwnerships.length}} matching relationships to local file:\\nownership_batch_${{sessionId}}.json\\n\\nThe file has been downloaded to your Downloads folder.`);
                }});
            }}
            
            // Reset all relationships
            function resetAllOwnerships() {{
                if (!confirm('Are you sure you want to reset all matching relationships? This will restore all hidden object boxes.')) {{
                    return;
                }}
                
                // Clear relationships map
                Object.keys(objectOwnershipMap).forEach(key => {{
                    delete objectOwnershipMap[key];
                }});
                
                // Clear local storage
                localStorage.removeItem('ownerships');
                localStorage.removeItem('all_ownerships');
                
                // Redraw TopCamera (restore all bboxes)
                // Note: drawTopCamera() will automatically call setupTopCameraDrag() and setupBboxInteractions()
                drawTopCamera();
                
                alert('All matching relationships have been reset!');
                console.log('匹配关系已重置');
            }}
    """
    
    return script
