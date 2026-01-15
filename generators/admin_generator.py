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
            transition: transform 0.2s;
        }
        .pool-card:hover { transform: translateY(-2px); }
        
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
        
        .participants-table {
            width: 100%;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .participants-table th {
            background: #667eea;
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
        }
        .participants-table td {
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
        }
        .participants-table tr:hover { background: #f7fafc; }
        
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
        
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            margin-left: 20px;
        }
        .refresh-btn:hover { background: #5a67d8; }
        
        .config-info {
            background: #f7fafc;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-family: monospace;
            font-size: 13px;
        }
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
        <div class="pool-card">
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
        status_class = "status-" + p.get('status', 'unknown').replace(' ', '-').lower()
        participants_rows += f"""
        <tr>
            <td>{p.get('user_id', 'N/A')[:20]}...</td>
            <td>{p.get('pool', '-')}</td>
            <td>{p.get('completed', 0)}/{p.get('total', 0)}</td>
            <td><span class="status-badge {status_class}">{p.get('status', 'Unknown')}</span></td>
            <td>{p.get('start_time', 'N/A')}</td>
            <td>{p.get('demographics', {}).get('nationality', '-')}</td>
        </tr>
        """
    
    if not participants_rows:
        participants_rows = '<tr><td colspan="6" style="text-align:center; color:#718096;">No participants yet</td></tr>'
    
    total_abandoned = total_started - total_completed
    
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
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
    </div>
    
    <div class="admin-container">
        <div class="config-info">
            <strong>Config:</strong> SCENES_ROOT = {config_info.get('scenes_root', 'N/A')} | 
            Total Scenes = {config_info.get('total_scenes', 0)} |
            Pools = 6 | 
            Scenes per Pool = {config_info.get('scenes_per_pool', 20)}
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
                <div class="value">{(total_completed/total_started*100) if total_started > 0 else 0:.1f}%</div>
            </div>
        </div>
        
        <h2 class="section-title">Pool Status</h2>
        <div class="stats-grid">
            {pool_cards_html}
        </div>
        
        <h2 class="section-title">Recent Participants</h2>
        <table class="participants-table">
            <thead>
                <tr>
                    <th>User ID</th>
                    <th>Pool</th>
                    <th>Progress</th>
                    <th>Status</th>
                    <th>Start Time</th>
                    <th>Nationality</th>
                </tr>
            </thead>
            <tbody>
                {participants_rows}
            </tbody>
        </table>
    </div>
    
    <script>
        // Auto refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""
