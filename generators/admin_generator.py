"""
Admin Dashboard Generator
=========================
Generates the admin dashboard for monitoring pool status and participant progress.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from static_assets.ui_components import render_common_css


def generate_admin_html(pool_status, participants_summary, config_info):
    """
    Generate admin dashboard HTML.
    
    Args:
        pool_status: Dict with pool stats {"1": {"started": 5, "completed": 3}, ...}
        participants_summary: List of participant info dicts
        config_info: Dict with config information
    """
    common_css = render_common_css()
    
    admin_css = """
        .admin-container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
        }
        
        /* ... (保留之前的样式: .header-actions, .stats-grid, .pool-card 等) ... */
        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 16px;
            margin-bottom: 30px;
        }
        .pool-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }
        .pool-card:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
        }
        .pool-id {
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 8px;
        }
        .pool-stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-top: 1px solid #eee;
            font-size: 14px;
        }
        .pool-stat-label { color: #666; }
        .pool-stat-value { font-weight: 600; }
        .stat-started { color: #f6ad55; }
        .stat-completed { color: #48bb78; }
        .stat-abandoned { color: #fc8181; }
        .progress-bar {
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            margin-top: 12px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #38a169);
            border-radius: 4px;
            transition: width 0.3s;
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #2d3748;
            margin: 30px 0 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        
        /* === 修改开始: 表格滚动容器与粘性表头 === */
        
        /* 新增：滚动容器 wrapper */
        .table-scroll-wrapper {
            max-height: 600px;       /* 限制最大高度，超过则滚动 */
            overflow-y: auto;        /* 启用垂直滚动条 */
            background: white;
            border-radius: 12px;     /* 圆角移动到容器上 */
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid #eee;
        }
        
        /* 自定义滚动条样式 (Webkit浏览器) */
        .table-scroll-wrapper::-webkit-scrollbar { width: 8px; }
        .table-scroll-wrapper::-webkit-scrollbar-track { background: #f1f1f1; }
        .table-scroll-wrapper::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 4px; }
        .table-scroll-wrapper::-webkit-scrollbar-thumb:hover { background: #a0aec0; }

        .participants-table {
            width: 100%;
            background: white;
            /* border-radius: 12px;  <-- 移除，由 wrapper 接管 */
            /* overflow: hidden;     <-- 移除 */
            /* box-shadow: ...       <-- 移除，由 wrapper 接管 */
            border-collapse: separate; /* 必须设置，否则 sticky 表头可能失效 */
            border-spacing: 0;
        }
        
        .participants-table th {
            /* 新增：粘性定位，滚动时表头固定在顶部 */
            position: sticky;
            top: 0;
            z-index: 10;
            
            background: #667eea;
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
        }
        
        .participants-table td {
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
            background: white; /* 防止文字重叠时透明 */
        }
        .participants-table tr:last-child td {
            border-bottom: none;
        }
        .participants-table tr:hover td { background: #f7fafc; }
        
        /* === 修改结束 === */

        .status-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-completed { background: #c6f6d5; color: #276749; }
        .status-in-progress { background: #feebc8; color: #c05621; }
        .status-abandoned { background: #fed7d7; color: #c53030; }
        .status-tutorial { background: #e9d8fd; color: #6b46c1; }
        
        /* ... (保留之后的样式: .summary-cards, .modal 等) ... */
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .summary-card h3 {
            font-size: 14px;
            color: #718096;
            margin-bottom: 8px;
        }
        .summary-card .value {
            font-size: 36px;
            font-weight: 700;
            color: #2d3748;
        }
        .refresh-btn, .download-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .refresh-btn:hover, .download-btn:hover { background: #5a67d8; }
        .download-btn { background: #48bb78; }
        .download-btn:hover { background: #38a169; }
        .view-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
        }
        .view-btn:hover { background: #5a67d8; }
        .config-info {
            background: #f7fafc;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-family: monospace;
            font-size: 13px;
        }
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-overlay.active { display: flex; }
        .modal-content {
            background: white;
            border-radius: 16px;
            max-width: 900px;
            width: 90%;
            max-height: 85vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .modal-header {
            background: #667eea;
            color: white;
            padding: 20px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-header h2 { margin: 0; font-size: 20px; }
        .modal-close {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .modal-close:hover { background: rgba(255,255,255,0.3); }
        .modal-body { padding: 24px; overflow-y: auto; flex: 1; }
        .modal-loading { text-align: center; padding: 40px; color: #718096; }
        .detail-section { margin-bottom: 24px; }
        .detail-section h3 {
            font-size: 16px;
            color: #2d3748;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e2e8f0;
        }
        .detail-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
        .detail-item { background: #f7fafc; padding: 12px; border-radius: 8px; }
        .detail-item label { font-size: 12px; color: #718096; display: block; margin-bottom: 4px; }
        .detail-item span { font-weight: 600; color: #2d3748; }
        .experiment-table { width: 100%; border-collapse: collapse; }
        .experiment-table th { background: #edf2f7; padding: 10px 12px; text-align: left; font-size: 13px; color: #4a5568; }
        .experiment-table td { padding: 10px 12px; border-bottom: 1px solid #edf2f7; font-size: 13px; }
        .slider-bar {
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            width: 100px;
            display: inline-block;
            margin-right: 8px;
            vertical-align: middle;
        }
        .slider-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
        .slider-fill.left { background: linear-gradient(90deg, #fc8181, #f56565); }
        .slider-fill.right { background: linear-gradient(90deg, #63b3ed, #4299e1); }
        .slider-fill.neutral { background: linear-gradient(90deg, #a0aec0, #718096); }
        .scene-group { margin-bottom: 24px; background: #f7fafc; border-radius: 12px; overflow: hidden; }
        .scene-header { background: #edf2f7; padding: 12px 16px; font-weight: 600; color: #2d3748; border-bottom: 1px solid #e2e8f0; }
        .pool-stats-table { width: 100%; border-collapse: collapse; }
        .pool-stats-table th { background: #e2e8f0; padding: 10px 16px; text-align: left; font-size: 13px; font-weight: 600; color: #4a5568; }
        .pool-stats-table td { padding: 10px 16px; border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #2d3748; }
        .pool-stats-table tr:last-child td { border-bottom: none; }
        .pool-stats-table .obj-name { font-weight: 500; }
        .pool-stats-table .mean-left { color: #e53e3e; font-weight: 600; }
        .pool-stats-table .mean-right { color: #3182ce; font-weight: 600; }
        .pool-stats-table .mean-neutral { color: #718096; font-weight: 600; }
    """
    
    # Build pool cards HTML
    pool_cards_html = ""
    total_started = 0
    total_completed = 0
    
    for pool_id in sorted(pool_status.keys(), key=int):
        stats = pool_status[pool_id]
        started = stats.get('started', 0)
        completed = stats.get('completed', 0)
        abandoned = started - completed
        
        total_started += started
        total_completed += completed
        
        # Calculate progress percentage (assuming target is configurable)
        target = config_info.get('target_per_pool', 10)
        progress_pct = min(100, (completed / target) * 100) if target > 0 else 0
        
        pool_cards_html += f"""
        <div class="pool-card" onclick="showPoolStats('{pool_id}')">
            <div class="pool-id">Pool {pool_id}</div>
            <div class="pool-stat">
                <span class="pool-stat-label">Started</span>
                <span class="pool-stat-value stat-started">{started}</span>
            </div>
            <div class="pool-stat">
                <span class="pool-stat-label">Completed</span>
                <span class="pool-stat-value stat-completed">{completed}</span>
            </div>
            <div class="pool-stat">
                <span class="pool-stat-label">Abandoned</span>
                <span class="pool-stat-value stat-abandoned">{abandoned}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {progress_pct:.1f}%"></div>
            </div>
            <div style="font-size: 12px; color: #718096; margin-top: 6px;">
                {progress_pct:.1f}% of target ({target})
            </div>
        </div>
        """
    
    # Build participants table HTML
    participants_rows = ""
    for p in participants_summary:
        # Extract participant_id from demographics for display
        participant_id = p.get('demographics', {}).get('participant_id', '-')
        user_id_full = p.get('user_id', '')
        status_class = "status-" + p.get('status', 'unknown').replace(' ', '-').lower()
        user_id = p.get('user_id', 'N/A')
        participants_rows += f"""
        <tr>
            <td title="{user_id_full}">{participant_id}</td>
            <td>{p.get('pool', '-')}</td>
            <td>{p.get('completed', 0)}/{p.get('total', 0)}</td>
            <td><span class="status-badge {status_class}">{p.get('status', 'Unknown')}</span></td>
            <td>{p.get('start_time', 'N/A')}</td>
            <td>{p.get('demographics', {}).get('nationality', '-')}</td>
            <td><button class="view-btn" onclick="showParticipantDetails('{user_id}')">View</button></td>
        </tr>
        """
    
    if not participants_rows:
        participants_rows = '<tr><td colspan="7" style="text-align:center; color:#718096;">No participants yet</td></tr>'
    
    total_abandoned = total_started - total_completed
    completion_rate = (total_completed/total_started*100) if total_started > 0 else 0
    
    # JavaScript for modal functionality
    modal_js = """
    const ADMIN_KEY = 'brain2026';
    
    function showModal(title) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = '<div class="modal-loading">Loading...</div>';
        document.getElementById('modalOverlay').classList.add('active');
    }
    
    function hideModal() {
        document.getElementById('modalOverlay').classList.remove('active');
    }
    
    function showParticipantDetails(userId) {
        showModal('Participant Details: ' + userId.substring(0, 20) + '...');
        
        fetch(`/api/participant/${userId}?key=${ADMIN_KEY}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('modalBody').innerHTML = `<div style="color:#c53030;">Error: ${data.error}</div>`;
                    return;
                }
                renderParticipantDetails(data);
            })
            .catch(err => {
                document.getElementById('modalBody').innerHTML = `<div style="color:#c53030;">Error: ${err.message}</div>`;
            });
    }
    
    function renderParticipantDetails(data) {
        const demo = data.demographics || {};
        const experiments = data.experiments || [];
        
        let html = `
            <div class="detail-section">
                <h3>📋 Demographics</h3>
                <div class="detail-grid">
                    <div class="detail-item"><label>Gender</label><span>${demo.gender || '-'}</span></div>
                    <div class="detail-item"><label>Date of Birth</label><span>${demo.dob || '-'}</span></div>
                    <div class="detail-item"><label>Nationality</label><span>${demo.nationality || '-'}</span></div>
                    <div class="detail-item"><label>Education</label><span>${demo.education || '-'}</span></div>
                    <div class="detail-item"><label>Status</label><span>${demo.status || '-'}</span></div>
                    <div class="detail-item"><label>IP Address</label><span>${demo.ip_address || '-'}</span></div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3>📊 Session Info</h3>
                <div class="detail-grid">
                    <div class="detail-item"><label>Pool</label><span>${data.assigned_pool || 'Not assigned'}</span></div>
                    <div class="detail-item"><label>Progress</label><span>${data.completed_scenes?.length || 0}/${data.total_scenes || 0}</span></div>
                    <div class="detail-item"><label>Start Time</label><span>${data.start_time?.substring(0, 16).replace('T', ' ') || '-'}</span></div>
                </div>
            </div>
        `;
        
        if (experiments.length > 0) {
            html += `
                <div class="detail-section">
                    <h3>🎯 Experiment Results (${experiments.length} scenes)</h3>
                    <table class="experiment-table">
                        <thead>
                            <tr>
                                <th>Scene</th>
                                <th>Object</th>
                                <th>Slider Value</th>
                                <th>Choice</th>
                                <th>Duration</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            experiments.forEach(exp => {
                const results = exp.results || [];
                const duration = exp.duration_ms ? (exp.duration_ms / 1000).toFixed(1) + 's' : '-';
                
                results.forEach((r, idx) => {
                    const val = r.slider_value ?? 50;
                    // Critical: value=50 must be shown as Neutral (gray), not converted to binary
                    let barClass, choice;
                    if (val === 50) {
                        barClass = 'neutral';
                        choice = '⬤ Unsure';
                    } else if (val < 50) {
                        barClass = 'left';
                        choice = '← Left (Agent A)';
                    } else {
                        barClass = 'right';
                        choice = 'Right (Agent B) →';
                    }
                    
                    html += `
                        <tr>
                            <td>${idx === 0 ? exp.scene : ''}</td>
                            <td>${r.object_id || '-'}</td>
                            <td>
                                <div class="slider-bar">
                                    <div class="slider-fill ${barClass}" style="width: ${val}%"></div>
                                </div>
                                <span>${val}</span>
                            </td>
                            <td>${choice}</td>
                            <td>${idx === 0 ? duration : ''}</td>
                        </tr>
                    `;
                });
            });
            
            html += '</tbody></table></div>';
        } else {
            html += '<div style="color:#718096; text-align:center; padding:20px;">No experiment data yet</div>';
        }
        
        document.getElementById('modalBody').innerHTML = html;
    }
    
    function showPoolStats(poolId) {
        showModal('Pool ' + poolId + ' Aggregate Statistics');
        
        fetch(`/api/pool_stats/${poolId}?key=${ADMIN_KEY}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('modalBody').innerHTML = `<div style="color:#c53030;">Error: ${data.error}</div>`;
                    return;
                }
                renderPoolStats(data, poolId);
            })
            .catch(err => {
                document.getElementById('modalBody').innerHTML = `<div style="color:#c53030;">Error: ${err.message}</div>`;
            });
    }
    
    function renderPoolStats(data, poolId) {
        const scenes = Object.keys(data);
        
        if (scenes.length === 0) {
            document.getElementById('modalBody').innerHTML = '<div style="color:#718096; text-align:center; padding:40px;">No data collected for Pool ' + poolId + ' yet.</div>';
            return;
        }
        
        let html = `<p style="color:#718096; margin-bottom:20px;">Aggregated statistics from all participants in Pool ${poolId}.</p>`;
        
        scenes.sort().forEach(sceneName => {
            const objects = data[sceneName];
            const objectIds = Object.keys(objects);
            
            html += `
                <div class="scene-group">
                    <div class="scene-header">🎬 ${sceneName}</div>
                    <table class="pool-stats-table">
                        <thead>
                            <tr>
                                <th>Object</th>
                                <th>Mean</th>
                                <th>Std Dev</th>
                                <th>N</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            objectIds.forEach(objId => {
                const stats = objects[objId];
                const mean = stats.mean;
                const stdDev = stats.std_dev;
                const n = stats.n;
                
                // Color class based on mean (50 is neutral center)
                let meanClass;
                if (mean < 50) {
                    meanClass = 'mean-left';
                } else if (mean > 50) {
                    meanClass = 'mean-right';
                } else {
                    meanClass = 'mean-neutral';
                }
                
                html += `
                    <tr>
                        <td class="obj-name">${objId}</td>
                        <td class="${meanClass}">${mean.toFixed(2)}</td>
                        <td>${stdDev.toFixed(2)}</td>
                        <td>${n}</td>
                    </tr>
                `;
            });
            
            html += '</tbody></table></div>';
        });
        
        document.getElementById('modalBody').innerHTML = html;
    }
    
    // Close modal on overlay click
    document.addEventListener('DOMContentLoaded', function() {
        document.getElementById('modalOverlay').addEventListener('click', function(e) {
            if (e.target === this) hideModal();
        });
    });
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') hideModal();
    });
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard</title>
    <style>
        {common_css}
        {admin_css}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Admin Dashboard</h1>
        <div class="header-actions">
            <a href="/admin/download_zip?key=brain2026" class="download-btn">📥 Download All Data (ZIP)</a>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>
    </div>
    
    <div class="admin-container">
        <div class="config-info">
            <strong>Config:</strong> SCENES_ROOT = {config_info.get('scenes_root', 'N/A')} | 
            Total Scenes = {config_info.get('total_scenes', 0)} |
            Pools = {config_info.get('num_pools', 6)} | 
            Scenes per Pool ≈ {config_info.get('scenes_per_pool', 20)} |
            Target per Pool = {config_info.get('target_per_pool', 20)}
        </div>
        
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Total Participants</h3>
                <div class="value">{total_started}</div>
            </div>
            <div class="summary-card">
                <h3>Completed Sessions</h3>
                <div class="value" style="color: #48bb78;">{total_completed}</div>
            </div>
            <div class="summary-card">
                <h3>Abandoned</h3>
                <div class="value" style="color: #fc8181;">{total_abandoned}</div>
            </div>
            <div class="summary-card">
                <h3>Completion Rate</h3>
                <div class="value">{completion_rate:.1f}%</div>
            </div>
        </div>
        
        <h2 class="section-title">Pool Status <span style="font-size:14px; font-weight:400; color:#718096;">(Click a pool card for aggregate stats)</span></h2>
        <div class="stats-grid">
            {pool_cards_html}
        </div>
        
        <h2 class="section-title">Recent Participants</h2>
        
        <div class="table-scroll-wrapper">
            <table class="participants-table">
                <thead>
                    <tr>
                        <th>Participant ID</th>
                        <th>Pool</th>
                        <th>Progress</th>
                        <th>Status</th>
                        <th>Start Time</th>
                        <th>Nationality</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {participants_rows}
                </tbody>
            </table>
        </div>
        </div>
    
    <div id="modalOverlay" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Details</h2>
                <button class="modal-close" onclick="hideModal()">✕</button>
            </div>
            <div class="modal-body" id="modalBody">
                </div>
        </div>
    </div>
    
    <script>
        {modal_js}
        
        // Auto refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""