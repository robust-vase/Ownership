"""
相机视角面板生成器
负责生成所有相机图片及其bbox标注的HTML代码
"""

def generate_camera_panel_html(camera_images, images_relative_path, projections, image_width=4096, image_height=4096):
    """
    生成相机视角面板的HTML内容
    
    Args:
        camera_images: 相机图片文件列表
        images_relative_path: 图片相对路径
        projections: 投影数据字典
        image_width: 图片宽度
        image_height: 图片高度
    
    Returns:
        HTML字符串
    """
    camera_count = len(camera_images)
    
    html = f"""
            <!-- 左侧：相机图片区域 -->
            <div class="camera-panel">
                <div class="panel-title">相机视角 ({camera_count} 张图片)</div>
                <div class="image-grid">
    """
    
    # 添加每张相机图片
    for i, image_file in enumerate(camera_images):
        image_name = image_file.name
        html += f"""
                    <div class="image-container">
                        <div class="image-wrapper">
                            <img src="{images_relative_path}/{image_name}" 
                                 alt="Camera {i+1}" 
                                 class="camera-image" 
                                 id="camera-img-{i}">
                            <svg class="bbox-overlay" id="bbox-svg-{i}"></svg>
                        </div>
                        <div class="image-label">Camera {i+1}</div>
                    </div>
        """
    
    html += """
                </div>
            </div>
    """
    
    return html


def generate_camera_bbox_script(camera_count, image_width=4096, image_height=4096):
    """
    生成相机bbox绘制的JavaScript代码
    
    Args:
        camera_count: 相机数量
        image_width: 图片宽度
        image_height: 图片高度
    
    Returns:
        JavaScript代码字符串
    """
    script = f"""
            // ==================== 相机图片bbox绘制 ====================
            const imageWidth = {image_width};
            const imageHeight = {image_height};
            
            function drawBboxOnCamera(cameraKey, svgId, imgId) {{
                const svgElement = document.getElementById(svgId);
                const imgElement = document.getElementById(imgId);
                
                if (!svgElement || !imgElement) return;
                
                // 等待图片加载完成
                if (!imgElement.complete) {{
                    imgElement.onload = () => drawBboxOnCamera(cameraKey, svgId, imgId);
                    return;
                }}
                
                // 获取图片的实际显示尺寸
                const displayWidth = imgElement.clientWidth;
                const displayHeight = imgElement.clientHeight;
                
                // 计算缩放比例
                const scaleX = displayWidth / imageWidth;
                const scaleY = displayHeight / imageHeight;
                
                // 设置SVG尺寸
                svgElement.setAttribute('viewBox', `0 0 ${{displayWidth}} ${{displayHeight}}`);
                
                // 清空现有内容
                svgElement.innerHTML = '';
                
                // 获取该相机的投影数据
                const cameraProjections = projections[cameraKey] || {{}};
                
                // 绘制每个物体的bbox
                Object.entries(cameraProjections).forEach(([objectId, projection]) => {{
                    // 只绘制个人物品（非房间物品）
                    if (projection.owner === 'room' || !projection.visible) return;
                    
                    const [xMin, yMin, xMax, yMax] = projection.bbox;
                    
                    // 转换到显示坐标
                    const x = xMin * scaleX;
                    const y = yMin * scaleY;
                    const width = (xMax - xMin) * scaleX;
                    const height = (yMax - yMin) * scaleY;
                    
                    // 创建组
                    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                    g.setAttribute('class', 'bbox-group');
                    g.setAttribute('data-object-id', objectId);
                    
                    // 创建矩形
                    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    rect.setAttribute('x', x);
                    rect.setAttribute('y', y);
                    rect.setAttribute('width', width);
                    rect.setAttribute('height', height);
                    rect.setAttribute('class', 'bbox-rect');
                    
                    g.appendChild(rect);
                    
                    // 创建标签
                    const centerX = x + width / 2;
                    const labelY = y - 5;
                    
                    // 标签背景
                    const textBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    textBg.setAttribute('class', 'bbox-label-bg');
                    textBg.setAttribute('rx', 2);
                    
                    // 标签文字
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
                    
                    // 在添加到DOM后更新背景尺寸
                    setTimeout(() => {{
                        try {{
                            const bbox = text.getBBox();
                            textBg.setAttribute('x', bbox.x - 3);
                            textBg.setAttribute('y', bbox.y - 2);
                            textBg.setAttribute('width', bbox.width + 6);
                            textBg.setAttribute('height', bbox.height + 4);
                        }} catch (e) {{
                            // getBBox可能失败，忽略
                        }}
                    }}, 10);
                }});
            }}
            
            // 为所有相机绘制bbox
            const cameraCount = {camera_count};
            for (let i = 0; i < cameraCount; i++) {{
                drawBboxOnCamera(i, `bbox-svg-${{i}}`, `camera-img-${{i}}`);
            }}
    """
    
    return script
