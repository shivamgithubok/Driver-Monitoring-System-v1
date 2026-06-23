import os

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DMS — Driver Monitoring System</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-dim: #334155;
      --border: #334155;
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --accent: #38bdf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --info: #3b82f6;
      --purple: #8b5cf6;
      --radius: 12px;
      --shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', system-ui, sans-serif; background-color: var(--bg); color: var(--text-primary); height: 100vh; width: 100vw; display: flex; overflow: hidden; padding: 0; }
    
    .app-container { display: flex; width: 100%; height: 100%; }
    
    .sidebar { width: 260px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 20px 0; z-index: 10; }
    .brand { display: flex; align-items: center; gap: 12px; padding: 0 24px 24px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
    .brand-icon { width: 40px; height: 40px; border-radius: 50%; background: #fff; display:flex; align-items:center; justify-content:center; color:#000; font-weight:800; font-size:20px; }
    .brand-text h1 { font-size: 18px; font-weight: 800; }
    .brand-text p { font-size: 11px; color: var(--text-secondary); }
    
    .nav-list { display: flex; flex-direction: column; gap: 4px; padding: 0 12px; flex: 1; overflow-y: auto; }
    .nav-item { padding: 12px 16px; border-radius: 8px; color: var(--text-secondary); font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: all 0.2s; }
    .nav-item:hover { background: var(--surface-dim); color: var(--text-primary); }
    .nav-item.active { background: rgba(16,185,129,0.1); color: var(--accent); }
    
    .sidebar-footer { padding: 16px 24px; border-top: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
    .user-avatar { width: 36px; height: 36px; border-radius: 50%; background: #be185d; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; }
    .user-info h4 { font-size: 13px; font-weight: 600; }
    .user-info p { font-size: 11px; color: var(--text-secondary); display:flex; align-items:center; gap:4px; }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--success); }
    
    .main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
    .view-container { display: none; flex: 1; flex-direction: column; padding: 20px; gap: 20px; overflow: hidden; animation: fadeIn 0.3s ease; padding: 12px; gap: 12px; }
    .view-container.active { display: flex; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    
    .top-bar { display: flex; justify-content: space-between; align-items: center; }
    .top-left h2 { font-size: 20px; font-weight: 700; display:flex; align-items:center; gap:8px;}
    .top-left p { font-size: 12px; color: var(--text-secondary); margin-top:4px; }
    .system-status { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text-secondary); }
    .system-status .dot { width:8px; height:8px; border-radius:50%; background:var(--success); }
    
    .top-right { display: flex; gap: 12px; align-items: center; }
    .metric-badge { background: var(--surface); border: 1px solid var(--border); padding: 8px 12px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; gap: 2px; }
    .metric-badge .lbl { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; }
    .metric-badge .val { font-size: 14px; font-weight: 700; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
    
    .stats-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; }
    .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; display: flex; flex-direction: column; gap: 8px; }
    .stat-card .lbl { display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text-secondary); font-weight:600; }
    .stat-card .val { font-size: 24px; font-weight: 700; display:flex; align-items:baseline; gap:8px; }
    .stat-card .sub { font-size: 12px; font-weight: 600; }
    .stat-card.green .val { color: var(--success); } .stat-card.red .val { color: var(--danger); } .stat-card.orange .val { color: var(--warning); } .stat-card.blue .val { color: var(--info); }
    
    .middle-row { display: grid; grid-template-columns: 2.5fr 1fr 1.5fr; gap: 16px; }
    
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; display: flex; flex-direction: column; }
    .card-header { padding: 12px 16px; border-bottom: 1px solid var(--border); font-size: 14px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
    .card-body { padding: 16px; flex: 1; overflow: hidden; display:flex; flex-direction:column; gap:12px; }
    
    .video-box { position: relative; background: #000; height: 100%; min-height: 250px; border-radius: var(--radius); overflow: hidden; }
    .video-box img { width: 100%; height: 100%; object-fit: contain; }
    .video-overlay-top { position: absolute; top:12px; left:12px; font-size:12px; font-weight:600; }
    
    .state-list { display: flex; flex-direction: column; gap: 12px; }
    .state-item { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
    .state-item .lbl { display:flex; align-items:center; gap:8px; color:var(--text-secondary); }
    .state-item .val { font-weight: 600; }
    .state-item .pct { font-family: 'JetBrains Mono'; font-size: 11px; color:var(--text-secondary); width: 30px; text-align:right;}
    .val.green { color: var(--success); } .val.red { color: var(--danger); } .val.blue { color: var(--info); }
    
    /* REFINED IDENTITY CARD */
    .id-card { display: flex; gap: 20px; align-items: center; }
    .id-avatar { width: 85px; height: 85px; border-radius: 50%; border: 2px solid var(--success); padding: 3px; position:relative; flex-shrink:0;}
    .id-avatar img { width: 100%; height: 100%; border-radius: 50%; object-fit:cover; background:#1f2937;}
    .id-badge { position: absolute; bottom:-4px; right:-4px; background: rgba(16,185,129,0.15); border-radius:50%; width:26px; height:26px; display:flex; align-items:center; justify-content:center; color:var(--success); border:1px solid var(--success); font-size:12px;}
    .id-details { flex: 1; font-size:11px; display:flex; flex-direction:column; gap:8px; }
    .id-row { display:flex; justify-content:space-between; }
    .id-row .lbl { color: var(--text-secondary); }
    .id-row .val { font-weight: 600; font-family: 'JetBrains Mono'; }
    .id-status-row { display:flex; justify-content:space-between; border-top: 1px solid var(--border); padding-top: 8px; margin-top: 4px; }
    .id-status-row .lbl { color: var(--text-secondary); }
    .id-status-row .val { font-weight: 700; color:var(--success); font-size:12px; }
    
    /* REFINED TRANSCRIPT CARD */
    .ts-content { display:flex; align-items:center; gap:16px; margin-bottom: 8px; }
    .ts-icon { color: var(--success); font-size:24px; font-weight:bold; }
    .transcript-box { font-size: 14px; color: var(--text-primary); font-weight: 500; font-style: italic; line-height:1.4; flex:1;}
    .ts-stats { display: flex; justify-content: space-between; border-top: 1px solid var(--border); padding-top:12px; }
    .ts-stats div { display: flex; flex-direction: column; gap:4px; font-size: 11px; }
    .ts-stats .lbl { color: var(--text-secondary); font-weight:500; }
    .ts-stats .val { font-weight: 600; }
    .ts-stats .red { color: var(--danger); } .ts-stats .orange { color: var(--warning); } .ts-stats .green { color: var(--success); }
    
    /* REFINED RECENT ALERTS */
    .alert-list { display: flex; flex-direction: column; gap: 12px; overflow-y:auto; height:180px; }
    .alert-item { display:flex; align-items:flex-start; gap:12px; padding: 4px 0; font-size:11px; border-bottom:1px solid rgba(255,255,255,0.03); }
    .alert-item:last-child { border-bottom: none; }
    .alert-icon { width: 24px; height: 24px; border-radius: 4px; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:12px;}
    .alert-icon.danger { background: rgba(239,68,68,0.15); color: var(--danger); }
    .alert-icon.warning { background: rgba(245,158,11,0.15); color: var(--warning); }
    .alert-icon.info { background: rgba(59,130,246,0.15); color: var(--info); }
    .alert-time { width: 70px; color:var(--text-secondary); font-family:'JetBrains Mono'; padding-top:2px; }
    .alert-msg { flex:1; display:flex; flex-direction:column; gap:2px; }
    .alert-msg .title { font-weight:600; color:var(--text-primary); font-size:12px;}
    .alert-msg .sub { color:var(--text-secondary); }
    .alert-item .badge { padding: 2px 8px; border-radius:4px; font-weight:600; font-size:10px; margin-top:2px;}
    .badge.high { background: rgba(239,68,68,0.1); color: var(--danger); border:1px solid rgba(239,68,68,0.2); }
    .badge.medium { background: rgba(245,158,11,0.1); color: var(--warning); border:1px solid rgba(245,158,11,0.2); }
    .badge.low { background: rgba(16,185,129,0.1); color: var(--success); border:1px solid rgba(16,185,129,0.2); }
    .badge.info { background: rgba(59,130,246,0.1); color: var(--info); border:1px solid rgba(59,130,246,0.2); }
    
    .charts-row { display: grid; grid-template-columns: repeat(4, 1fr) 1.5fr; gap: 16px; }
    .chart-wrapper { height: 120px; width: 100%; position:relative; }
    
    /* Live Grid & Insights */
    .live-grid { display: grid; grid-template-columns: 1.2fr 1.5fr; gap: 20px; flex: 1; height: 100px;}
    .insights-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .insight-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }
    .insight-title { font-size: 11px; font-weight: 600; color: var(--text-secondary); display:flex; justify-content:space-between; margin-bottom: 12px; text-transform:uppercase; letter-spacing:0.5px;}
    .bar-row { margin-bottom: 10px; display:flex; flex-direction:column; gap:6px; }
    .bar-lbl { display: flex; justify-content: space-between; font-size: 12px; }
    .bar-lbl .val { font-family: 'JetBrains Mono'; color:var(--text-primary); }
    .bar-bg { height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; overflow:hidden; }
    .bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s ease; }
    
    .bar-fill.red { background: var(--danger); } .bar-fill.green { background: var(--success); } .bar-fill.blue { background: var(--info); } .bar-fill.purple { background: var(--purple); } .bar-fill.orange { background: var(--warning); }
    
    .live-charts-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; }
    .live-footer { display: flex; justify-content: space-between; padding: 16px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
    .footer-stat { display:flex; flex-direction:column; gap:4px; }
    .footer-stat .lbl { font-size: 11px; color: var(--text-secondary); display:flex; align-items:center; gap:6px; }
    .footer-stat .val { font-size: 14px; font-weight: 700; color: var(--success); }
    .footer-stat.neutral .val { color: var(--text-primary); }
    
    .primary-btn { background: var(--accent); color: #000; border: none; padding: 10px 16px; border-radius: 6px; font-weight: 600; font-size: 13px; cursor: pointer; transition: 0.2s; }
    .primary-btn:hover { filter: brightness(1.1); }
    .sec-btn { background: var(--surface-dim); border: 1px solid var(--border); color: var(--text-primary); }
    
    #alert-banner { position: absolute; top: 0; left: 0; right: 0; background: rgba(239, 68, 68, 0.95); color: #fff; text-align: center; padding: 8px; font-weight: 700; font-size:12px; letter-spacing: 1px; display: none; z-index: 20; }
    #alert-banner.active { display: block; }
    
    .overlay-modal { position: fixed; inset: 0; z-index: 100; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; opacity: 0; pointer-events: none; transition: opacity 0.3s; }
    .overlay-modal.visible { opacity: 1; pointer-events: auto; }
    .modal-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); width: 400px; padding: 24px; text-align: center; }
    .form-input { width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-dim); color: #fff; font-family: inherit; font-size: 14px; margin-bottom: 16px; outline: none; }
    
    #conn-overlay { position: fixed; inset: 0; z-index: 1000; background: var(--bg); display: flex; flex-direction: column; align-items: center; justify-content: center; transition: opacity 0.5s; }
    #conn-overlay.hidden { opacity: 0; pointer-events: none; }
    .spinner { width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 16px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div id="conn-overlay"><div class="spinner"></div><p style="font-weight:600; color:var(--text-secondary);">Connecting to DMS Pipeline...</p></div>

  <div class="app-container">
    <!-- Sidebar -->
    <div class="sidebar">
      <div class="brand">
        <div class="brand-icon">DMS</div>
        <div class="brand-text"><h1>DMS</h1><p>Driver Monitoring System</p></div>
      </div>
      <div class="nav-list">
        <div class="nav-item active" onclick="switchView('dashboard')">⊞ Dashboard</div>
        <div class="nav-item" onclick="switchView('live')">👁 Live Monitoring</div>
        <div class="nav-item">📊 Analytics</div>
        <div class="nav-item">🎙 Audio Analytics</div>
        <div class="nav-item" onclick="openFaceEnrolModal()">👤 Identity Verification</div>
        <div class="nav-item">🔔 Alert History</div>
        <div class="nav-item">📄 Reports</div>
        <div class="nav-item">⚙ Settings</div>
      </div>
      <div class="sidebar-footer">
        <div class="user-avatar">AK</div>
        <div class="user-info"><h4>Admin</h4><p>System Operator <span class="status-dot"></span> Online</p></div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-area">
            <!-- DASHBOARD -->
      <div id="view-dashboard" class="view-container active">
        <div class="top-bar">
          <div class="top-left">
            <div class="system-status"><span class="dot" id="model-dot"></span> <span id="model-status">System Active</span></div>
          </div>
          <div class="top-right">
            <div class="metric-badge"><span class="lbl">FPS</span><span class="val" id="dash-fps">28</span></div>
            <div class="metric-badge"><span class="lbl">MODEL</span><span class="val">TensorRT</span></div>
            <div class="metric-badge"><span class="lbl">DEVICE</span><span class="val">Orin Nano</span></div>
            <div style="width:1px; height:24px; background:var(--border); margin:0 8px;"></div>
            <button class="primary-btn sec-btn" onclick="openFaceEnrolModal()">🔒 Enroll Face</button>
            <button class="primary-btn" onclick="openEnrolModal()">🎤 Enroll Voice</button>
          </div>
        </div>
        
        <div class="stats-row">
          <div class="stat-card green"><span class="lbl">◬ Drowsiness Score</span><span class="val"><span id="dash-drowsy-pct">0</span>% <span class="sub" id="dash-drowsy-txt">Low</span></span></div>
          <div class="stat-card green"><span class="lbl">👁 Attention Score</span><span class="val"><span id="dash-attn-pct">100</span>% <span class="sub" id="dash-attn-txt">Good</span></span></div>
          <div class="stat-card red"><span class="lbl">🎙 Audio Risk Score</span><span class="val"><span id="dash-audio-pct">0</span>% <span class="sub" id="dash-audio-txt">Low</span></span></div>
          <div class="stat-card orange"><span class="lbl">⚠️ Active Alerts</span><span class="val"><span id="dash-active-alerts">0</span> <span class="sub">Warning</span></span></div>
          <div class="stat-card orange"><span class="lbl">🔔 Total Alerts</span><span class="val"><span id="alert-count">0</span> <span class="sub">Today</span></span></div>
          <div class="stat-card blue"><span class="lbl">⏱ Session Duration</span><span class="val" id="uptime">00:00:00</span></div>
        </div>
        
        <div class="dashboard-grid" style="display: grid; grid-template-columns: 3fr 1.2fr; gap: 12px; flex: 1; min-height: 0;">
          <!-- Left Main Area -->
          <div style="display: flex; flex-direction: column; gap: 12px; min-height: 0;">
            <!-- Top row: Video + Driver State -->
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 12px; flex: 1.5; min-height: 0;">
              <div class="card" style="padding:0;">
                <div class="video-box" style="height: 100%; border-radius: var(--radius);">
                  <div id="alert-banner">⚠️ CRITICAL: DROWSINESS DETECTED</div>
                  <div class="video-overlay-top" style="color:var(--success)">Live Camera Feed <span style="background:rgba(16,185,129,0.2); padding:2px 6px; border-radius:4px;">LIVE</span></div>
                  <img id="video-stream" src="/video_feed" alt="Feed" style="width:100%; height:100%; object-fit:cover;">
                </div>
              </div>
              <div class="card">
                <div class="card-header">Driver State</div>
                <div class="card-body state-list" style="justify-content:center; padding: 8px;">
                  <div class="state-item"><span class="lbl">😴 Drowsiness</span><span class="val green" id="ds-drowsy">Normal</span><span class="pct" id="ds-drowsy-p">0%</span></div>
                  <div class="state-item"><span class="lbl">👁 Eye State</span><span class="val green" id="ds-eye">Open</span><span class="pct" id="ds-eye-p">0%</span></div>
                  <div class="state-item"><span class="lbl">🥱 Yawning</span><span class="val green" id="ds-yawn">No</span><span class="pct" id="ds-yawn-p">0%</span></div>
                  <div class="state-item"><span class="lbl">🧭 Gaze Direction</span><span class="val green" id="ds-gaze">Forward</span><span class="pct" id="ds-gaze-p">0%</span></div>
                  <div class="state-item"><span class="lbl">🙂 Emotion</span><span class="val blue" id="ds-emotion">Neutral</span><span class="pct" id="ds-emotion-p">0%</span></div>
                  <div class="state-item"><span class="lbl">📱 Distraction</span><span class="val green" id="ds-dist">No</span><span class="pct" id="ds-dist-p">0%</span></div>
                </div>
              </div>
            </div>
            
            <!-- Charts Row -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; flex: 1; min-height: 0;">
              <div class="card"><div class="card-header">Drowsiness</div><div class="card-body" style="padding:4px;"><div class="chart-wrapper" style="height:100%;"><canvas id="chartDrowsy"></canvas></div></div></div>
              <div class="card"><div class="card-header">Audio Risk</div><div class="card-body" style="padding:4px;"><div class="chart-wrapper" style="height:100%;"><canvas id="chartAudio"></canvas></div></div></div>
              <div class="card"><div class="card-header">Gaze</div><div class="card-body" style="padding:4px;"><div class="chart-wrapper" style="height:100%;"><canvas id="chartGaze"></canvas></div></div></div>
              <div class="card"><div class="card-header">Attention</div><div class="card-body" style="padding:4px;"><div class="chart-wrapper" style="height:100%;"><canvas id="chartAttn"></canvas></div></div></div>
            </div>
            
            <!-- Activity Row -->
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 12px; flex: 1; min-height: 0;">
              <div class="card">
                <div class="card-header">Alert Dist (Today)</div>
                <div class="card-body" style="display:flex; justify-content:center; align-items:center;">
                  <!-- We can reuse chartGaze or make a new one -->
                  <div class="chart-wrapper" style="width:100px; height:100px;"><canvas id="chartAlerts"></canvas></div>
                </div>
              </div>
              <div class="card">
                <div class="card-header">Activity Summary</div>
                <div class="card-body" style="display:flex; justify-content:space-around; align-items:center;">
                  <div style="text-align:center;"><div style="font-size:20px; font-weight:700;" id="sum-drowsy">0</div><div style="font-size:10px; color:var(--text-secondary);">Drowsy Events</div></div>
                  <div style="text-align:center;"><div style="font-size:20px; font-weight:700;" id="sum-yawn">0</div><div style="font-size:10px; color:var(--text-secondary);">Yawning Events</div></div>
                  <div style="text-align:center;"><div style="font-size:20px; font-weight:700;" id="sum-phone">0</div><div style="font-size:10px; color:var(--text-secondary);">Phone Usage</div></div>
                  <div style="text-align:center;"><div style="font-size:20px; font-weight:700;" id="sum-audio">0</div><div style="font-size:10px; color:var(--text-secondary);">Audio Alerts</div></div>
                </div>
              </div>
            </div>
            
            <!-- System Resources Row -->
            <div class="card" style="flex: 0.5; display:flex; flex-direction:row; justify-content:space-between; align-items:center; padding: 0 16px; font-size:12px;">
              <div style="display:flex; flex-direction:column;"><span style="color:var(--text-secondary);">CPU Usage</span><span style="font-weight:700;">32%</span></div>
              <div style="display:flex; flex-direction:column;"><span style="color:var(--text-secondary);">GPU Usage</span><span style="font-weight:700;">68%</span></div>
              <div style="display:flex; flex-direction:column;"><span style="color:var(--text-secondary);">RAM Usage</span><span style="font-weight:700;">45%</span></div>
              <div style="display:flex; flex-direction:column;"><span style="color:var(--text-secondary);">Temperature</span><span style="font-weight:700;">62°C</span></div>
              <div style="display:flex; flex-direction:column;"><span style="color:var(--text-secondary);">TensorRT FPS</span><span style="font-weight:700;" id="sys-fps">28</span></div>
              <div style="display:flex; flex-direction:column;"><span style="color:var(--text-secondary);">Power Mode</span><span style="font-weight:700; color:var(--success);">MAXN</span></div>
            </div>
          </div>
          
          <!-- Right Sidebar Area -->
          <div style="display: flex; flex-direction: column; gap: 12px; min-height: 0;">
            <div class="card" style="flex: 1.2;">
              <div class="card-header">Driver Identity <span style="color:var(--success); font-size:11px; background:rgba(16,185,129,0.1); padding:2px 6px; border-radius:10px;">● Verified</span></div>
              <div class="card-body id-card" style="padding:12px;">
                <div class="id-avatar"><img src="/static/avatar-placeholder.png" alt="" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'%23fff\'%3E%3Cpath d=\'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z\'/%3E%3C/svg%3E';"><div class="id-badge">✓</div></div>
                <div class="id-details">
                  <div class="id-row"><span class="lbl">Driver</span><span class="val" id="face-name-val">Shivam</span></div>
                  <div class="id-row"><span class="lbl">Match</span><span class="val" id="face-sim-val">98.3%</span></div>
                  <div class="id-row"><span class="lbl">Liveness</span><span class="val" style="color:var(--success)" id="face-live-val">REAL</span></div>
                  <div class="id-row"><span class="lbl">Speaker</span><span class="val" id="voice-speaker" style="color:var(--success)">DRIVER</span></div>
                  <div class="id-status-row"><span class="lbl">Status</span><span class="val" id="face-match-badge">VERIFIED ✓</span></div>
                </div>
              </div>
            </div>
            <div class="card" style="flex: 1;">
              <div class="card-header">Live Transcript <span style="color:var(--success); font-size:11px; background:rgba(16,185,129,0.1); padding:2px 6px; border-radius:10px;">● Live</span></div>
              <div class="card-body" style="padding:12px;">
                <div class="ts-content" style="margin-bottom:4px;">
                  <div class="ts-icon">ılılı</div>
                  <div class="transcript-box" id="transcript-box">"I am feeling sleepy..."</div>
                </div>
                <div class="ts-stats">
                  <div><span class="lbl">Speaker</span><span class="val green" id="voice-speaker-stat">DRIVER</span></div>
                  <div><span class="lbl">Risk</span><span class="val red" id="voice-risk-score">0.82</span></div>
                  <div><span class="lbl">Keyword</span><span class="val orange" id="voice-keyword">sleepy</span></div>
                  <div><span class="lbl">Alert</span><span class="val orange" id="voice-alert-badge">WARNING</span></div>
                </div>
              </div>
            </div>
            <div class="card" style="flex: 2;">
              <div class="card-header">Recent Alerts <a href="#" style="font-size:11px; color:var(--text-secondary); text-decoration:none;">View All</a></div>
              <div class="card-body" style="padding:8px;">
                <div class="alert-list" id="alert-list" style="height:100%; max-height: 250px;"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- LIVE MONITORING -->
      <div id="view-live" class="view-container">
        <div class="top-bar">
          <div class="top-left"><h2>Live Monitoring</h2><p>Real-time driver analysis from vision pipeline</p></div>
          <div class="top-right">
            <div class="metric-badge"><span class="lbl">FPS</span><span class="val" style="color:var(--success);" id="live-fps">28</span></div>
            <div class="metric-badge"><span class="lbl">MODEL</span><span class="val">TensorRT</span></div>
            <div class="metric-badge"><span class="lbl">DEVICE</span><span class="val">Orin Nano</span></div>
            <div class="metric-badge"><span class="lbl">RESOLUTION</span><span class="val">640 x 480</span></div>
          </div>
        </div>
        
        <div class="live-grid">
          <div class="card" style="padding:16px;">
            <div class="video-box">
              <div class="video-overlay-top" style="color:var(--text-primary)">Live Camera Feed <span style="background:rgba(16,185,129,0.2); color:var(--success); padding:2px 6px; border-radius:4px; font-size:10px;">LIVE</span></div>
              <div class="vid-overlay-hud" style="position:absolute; top:40px; left:12px; background:rgba(0,0,0,0.6); padding:8px 12px; border-radius:8px; font-size:11px; border:1px solid rgba(255,255,255,0.1);">
                <div style="display:flex; justify-content:space-between; gap:16px;"><span style="color:var(--text-secondary)">Face:</span><span style="color:var(--success); font-weight:700;" id="hud-face">DETECTED</span></div>
                <div style="display:flex; justify-content:space-between; gap:16px;"><span style="color:var(--text-secondary)">Liveness:</span><span style="color:var(--success); font-weight:700;" id="hud-live">REAL</span></div>
                <div style="display:flex; justify-content:space-between; gap:16px;"><span style="color:var(--text-secondary)">Identity:</span><span style="color:var(--success); font-weight:700;" id="hud-id">VERIFIED</span></div>
                <div style="display:flex; justify-content:space-between; gap:16px;"><span style="color:var(--text-secondary)">Driver:</span><span style="color:var(--text-primary); font-weight:700;" id="active-driver-display">Unknown</span></div>
              </div>
            </div>
          </div>
          
          <div class="card" style="background:transparent; border:none;"><div class="insights-grid" id="insights-grid"></div></div>
        </div>
        
        <h3 style="font-size:13px; color:var(--text-secondary); text-transform:uppercase; font-weight:600; margin-top:5px;">Key Metrics Over Time</h3>
        <div class="live-charts-row">
          <div class="card"><div class="card-header">Drowsiness (%)</div><div class="card-body"><div class="chart-wrapper"><canvas id="cLive1"></canvas></div></div></div>
          <div class="card"><div class="card-header">Eye Closure (%)</div><div class="card-body"><div class="chart-wrapper"><canvas id="cLive2"></canvas></div></div></div>
          <div class="card"><div class="card-header">Yawning (%)</div><div class="card-body"><div class="chart-wrapper"><canvas id="cLive3"></canvas></div></div></div>
          <div class="card"><div class="card-header">Distracted Activity (%)</div><div class="card-body"><div class="chart-wrapper"><canvas id="cLive4"></canvas></div></div></div>
          <div class="card"><div class="card-header">Attention Score (%)</div><div class="card-body"><div class="chart-wrapper"><canvas id="cLive5"></canvas></div></div></div>
        </div>
        
        <div class="live-footer">
          <div class="footer-stat"><span class="lbl">📷 Face Detected</span><span class="val" id="foot-face">Yes</span></div>
          <div class="footer-stat"><span class="lbl">◎ Liveness Score</span><span class="val" id="foot-live">0.0</span></div>
          <div class="footer-stat"><span class="lbl">👤 Identity Match</span><span class="val" id="foot-id">0.0</span></div>
          <div class="footer-stat neutral"><span class="lbl">◷ Latency</span><span class="val" style="color:var(--accent)" id="foot-lat">22 ms</span></div>
          <div class="footer-stat neutral"><span class="lbl">⚙ Pipeline Status</span><span class="val" style="color:var(--success)">● Active</span></div>
        </div>
      </div>
    </div>
  </div>

  <!-- MODALS -->
  <div class="overlay-modal" id="enrol-overlay"><div class="modal-card"><div style="display:flex; justify-content:space-between; margin-bottom:12px;"><h2 class="modal-title">🎙️ Voice Enrollment</h2><button style="background:none; border:none; font-size:24px; cursor:pointer; color:var(--text-secondary);" onclick="closeEnrolModal()">&times;</button></div><div id="estep-1" style="display:block"><p class="modal-desc">Register your vocal fingerprint.</p><input type="text" class="form-input" id="driver-name-input" placeholder="Driver Full Name"><button class="primary-btn" id="enrol-begin-btn" onclick="startEnrolment()" style="width:100%;">Begin Sampling</button></div><div id="estep-2" style="display:none"><h3 id="enrol-pct">0%</h3><p id="enrol-phase-label" style="color:var(--accent);">RECORDING</p></div><div id="estep-3" style="display:none"><h3 id="enrol-result-title">Complete</h3><p id="enrol-result-msg" class="modal-desc"></p><button class="primary-btn" onclick="closeEnrolModal()" style="width:100%;">Done</button></div></div></div>
  <div class="overlay-modal" id="face-enrol-overlay"><div class="modal-card"><div style="display:flex; justify-content:space-between; margin-bottom:12px;"><h2 class="modal-title">🔒 Face Registration</h2><button style="background:none; border:none; font-size:24px; cursor:pointer; color:var(--text-secondary);" onclick="closeFaceEnrolModal()">&times;</button></div><div id="fstep-1" style="display:block"><p class="modal-desc">Save geometric embeddings.</p><input type="text" class="form-input" id="face-driver-name-input" placeholder="Driver Full Name"><button class="primary-btn" id="face-enrol-begin-btn" onclick="startFaceEnrolment()" style="width:100%;">Start Capture</button><button class="primary-btn sec-btn" style="margin-top:10px; width:100%;" onclick="toggleFaceVerify()" id="face-verify-toggle-btn">Start Verify Scan</button></div><div id="fstep-2" style="display:none"><h3 id="face-enrol-pct">0%</h3></div><div id="fstep-3" style="display:none"><h3 id="face-enrol-result-title">Registered</h3><p id="face-enrol-result-msg" class="modal-desc"></p><button class="primary-btn" onclick="closeFaceEnrolModal()" style="width:100%;">Done</button></div></div></div>

  <script>
    const TASK_META = {{ task_meta|safe }};
    const TASK_ORDER = {{ task_order|safe }};
    let alertCount = 0; let startTime = Date.now();
    
    Chart.defaults.color = '#9ca3af'; Chart.defaults.font.family = 'Inter';
    const commonOpt = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { display: true, min: 0, max: 100, border: {display: false}, grid: {color: '#1f2937'} } }, elements: { point: { radius: 0 }, line: { tension: 0.3, borderWidth: 2 } } };
    function createChart(ctxId, color, fill=true) { return new Chart(document.getElementById(ctxId), { type: 'line', data: { labels: Array(30).fill(''), datasets: [{ data: Array(30).fill(0), borderColor: color, backgroundColor: fill ? color+'20' : 'transparent', fill: fill }] }, options: commonOpt }); }
    
    const charts = { dashDrowsy: createChart('chartDrowsy', '#ef4444'), dashAudio: createChart('chartAudio', '#f59e0b'), dashGaze: new Chart(document.getElementById('chartGaze'), { type: 'doughnut', data: { labels: ['Fwd','Left','Right','Up','Down'], datasets: [{ data:[1,1,1,1,1], backgroundColor: ['#10b981','#3b82f6','#8b5cf6','#f59e0b','#ef4444'], borderWidth:0 }] }, options: {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'right', labels:{boxWidth:10, font:{size:10}}}}, cutout:'70%'} }), dashAttn: new Chart(document.getElementById('chartAttn'), { type: 'bar', data: { labels: Array(15).fill(''), datasets: [{ data: Array(15).fill(0), backgroundColor: '#10b981' }] }, options: {...commonOpt, scales:{x:{display:false}, y:{min:0, max:100, grid:{color:'#1f2937'}}}} }), l1: createChart('cLive1', '#ef4444'), l2: createChart('cLive2', '#10b981'), l3: createChart('cLive3', '#3b82f6'), l4: createChart('cLive4', '#f59e0b'), l5: createChart('cLive5', '#8b5cf6') };
    function updateChartData(chart, val) { if(chart.config.type === 'line' || chart.config.type === 'bar') { const d = chart.data.datasets[0].data; d.push(val); d.shift(); chart.update('none'); } }

    function buildInsights() {
      const grid = document.getElementById('insights-grid');
      const colors = ['red','green','blue','purple','orange','red']; let i = 0;
      for (const t of TASK_ORDER) {
        if (!TASK_META[t] || t === 'age' || t === 'gender') continue;
        const meta = TASK_META[t]; const clr = colors[i % colors.length]; i++;
        let barsHtml = '';
        for (const [clsId, clsName] of Object.entries(meta.classes)) { barsHtml += `<div class="bar-row"><div class="bar-lbl"><span>${clsName}</span><span class="val" id="bar-v-${t}-${clsName}">0.0%</span></div><div class="bar-bg"><div class="bar-fill ${clr}" id="bar-f-${t}-${clsName}" style="width:0%"></div></div></div>`; }
        grid.innerHTML += `<div class="insight-card"><div class="insight-title"><span>${meta.label} (${Object.keys(meta.classes).length} Classes)</span> <span>ⓘ</span></div>${barsHtml}</div>`;
      }
    }
    buildInsights();

    function switchView(v) {
      document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active')); event.currentTarget.classList.add('active');
      document.querySelectorAll('.view-container').forEach(el => el.classList.remove('active')); document.getElementById(`view-${v}`).classList.add('active');
      const vid = document.getElementById('video-stream');
      const targetBox = document.querySelector(`#view-${v} .video-box`);
      if (vid && targetBox) targetBox.appendChild(vid);
    }

    function updateUI(predictions, fps, audio = null) {
      document.getElementById("dash-fps").textContent = fps; document.getElementById("live-fps").textContent = fps;
      let drScore = 0; let eyeScore = 0; let yawnScore = 0; let distScore = 0; let attnScore = 100; let gazeArr = [0,0,0,0,0];
      
      for (const t of TASK_ORDER) {
        const p = predictions[t]; if (!p) continue; const meta = TASK_META[t];
        if (t === 'drowsiness') { const v = p.label; const conf = Math.round(p.confidence*100); document.getElementById('ds-drowsy').textContent = v; document.getElementById('ds-drowsy').className = 'val ' + (v==='Drowsy'?'red':'green'); document.getElementById('ds-drowsy-p').textContent = `${conf}%`; drScore = p.pred === meta.alert_class ? conf : 0; document.getElementById('dash-drowsy-pct').textContent = drScore; document.getElementById('dash-drowsy-txt').textContent = drScore > 60 ? 'High' : 'Low'; }
        if (t === 'eye_state') { document.getElementById('ds-eye').textContent = p.label; document.getElementById('ds-eye-p').textContent = `${Math.round(p.confidence*100)}%`; eyeScore = p.label==='Closed' ? Math.round(p.confidence*100) : 0; if (p.label==='Closed') attnScore -= 30; }
        if (t === 'yawn') { document.getElementById('ds-yawn').textContent = p.label; document.getElementById('ds-yawn-p').textContent = `${Math.round(p.confidence*100)}%`; yawnScore = p.label==='Yawning' ? Math.round(p.confidence*100) : 0; }
        if (t === 'gaze') { document.getElementById('ds-gaze').textContent = p.label; document.getElementById('ds-gaze-p').textContent = `${Math.round(p.confidence*100)}%`; if (p.label!=='Forward') attnScore -= 20; if(p.probs) { gazeArr = [ p.probs['Forward']||0, p.probs['Left']||0, p.probs['Right']||0, p.probs['Up']||0, p.probs['Down']||0 ]; charts.dashGaze.data.datasets[0].data = gazeArr; charts.dashGaze.update('none'); } }
        if (t === 'emotion') { document.getElementById('ds-emotion').textContent = p.label; document.getElementById('ds-emotion-p').textContent = `${Math.round(p.confidence*100)}%`; }
        if (t === 'activity') { const isDist = p.label!=='Safe Driving' && p.label!=='None'; document.getElementById('ds-dist').textContent = isDist ? p.label : 'No'; document.getElementById('ds-dist').className = 'val ' + (isDist?'red':'green'); document.getElementById('ds-dist-p').textContent = `${Math.round(p.confidence*100)}%`; distScore = isDist ? Math.round(p.confidence*100) : 0; if (isDist) attnScore -= 40; }

        if (p.probs) {
          for (const [clsId, clsName] of Object.entries(meta.classes)) {
            const prob = p.probs[clsName] || 0; const pct = (prob * 100).toFixed(1);
            const lblEl = document.getElementById(`bar-v-${t}-${clsName}`); const barEl = document.getElementById(`bar-f-${t}-${clsName}`);
            if (lblEl) lblEl.textContent = `${pct}%`; if (barEl) barEl.style.width = `${pct}%`;
          }
        }
      }
      attnScore = Math.max(0, attnScore); document.getElementById('dash-attn-pct').textContent = attnScore; document.getElementById('dash-attn-txt').textContent = attnScore > 70 ? 'Good' : 'Poor';
      updateChartData(charts.dashDrowsy, drScore); updateChartData(charts.dashAttn, attnScore); updateChartData(charts.l1, drScore); updateChartData(charts.l2, eyeScore); updateChartData(charts.l3, yawnScore); updateChartData(charts.l4, distScore); updateChartData(charts.l5, attnScore);
      const banner = document.getElementById("alert-banner"); if (drScore > 60 || attnScore < 30) { banner.classList.add("active"); } else { banner.classList.remove("active"); }
    }

    function logAlert(msg, level = "warn") {
      const list = document.getElementById("alert-list"); const time = new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
      const item = document.createElement("div"); item.className = `alert-item`;
      let icnClass = 'warning'; let icon = '⚠️'; let badgeClass = 'medium'; let badgeTxt = 'Medium';
      if(level==='danger'){ icnClass='danger'; icon='🚨'; badgeClass='high'; badgeTxt='High'; }
      if(level==='info'){ icnClass='info'; icon='ℹ'; badgeClass='info'; badgeTxt='Info'; }
      
      item.innerHTML = `<div class="alert-icon ${icnClass}">${icon}</div><div class="alert-time">${time}</div><div class="alert-msg"><span class="title">${msg}</span><span class="sub">Duration: 2.0s</span></div><div class="badge ${badgeClass}">${badgeTxt}</div>`;
      list.prepend(item); while (list.children.length > 20) list.lastChild.remove();
      alertCount++; document.getElementById("alert-count").textContent = alertCount; document.getElementById("dash-active-alerts").textContent = level==='danger' ? parseInt(document.getElementById("dash-active-alerts").textContent)+1 : document.getElementById("dash-active-alerts").textContent;
    }
    
    // Add some dummy alerts for visual testing just to match layout initially
    setTimeout(()=>{logAlert("Audio Risk High", "danger");}, 1000);
    setTimeout(()=>{logAlert("Drowsiness Detected", "warn");}, 2000);
    setTimeout(()=>{logAlert("Safe Driving", "info");}, 3000);

    setInterval(() => { const s = Math.floor((Date.now() - startTime) / 1000); document.getElementById("uptime").textContent = `${String(Math.floor(s / 3600)).padStart(2,'0')}:${String(Math.floor((s % 3600) / 60)).padStart(2,'0')}:${String(s % 60).padStart(2,'0')}`; }, 1000);

    function connectSSE() { const evtSource = new EventSource("/predictions"); evtSource.onopen = () => document.getElementById("conn-overlay").classList.add("hidden"); evtSource.onmessage = (e) => { const { predictions, fps, audio } = JSON.parse(e.data); updateUI(predictions, fps, audio); }; evtSource.onerror = () => { setTimeout(() => { if (evtSource.readyState === EventSource.CLOSED) { document.getElementById("conn-overlay").classList.remove("hidden"); connectSSE(); } }, 2000); }; }
    function connectAudioSSE() { const audioSource = new EventSource("/audio_events"); audioSource.onmessage = (e) => { const ev = JSON.parse(e.data); let msg = `Audio: ${ev.label}`; if (ev.kw) msg += ` (KW: ${ev.kw})`; logAlert(msg, (ev.level === "CRITICAL" || ev.level === "ALERT") ? "danger" : "warn"); }; }

    async function pollVoiceResults() {
      try {
        const r = await fetch("/voice_results"); const data = await r.json();
        if (data.transcript) document.getElementById("transcript-box").textContent = `"${data.transcript}"`;
        document.getElementById("voice-keyword").textContent = data.keyword ? data.keyword : "—";
        document.getElementById("voice-speaker").textContent = data.speaker ? data.speaker : "—";
        document.getElementById("voice-speaker-stat").textContent = data.speaker ? data.speaker : "—";
        const risk = data.fusion_score || 0; document.getElementById("dash-audio-pct").textContent = Math.round(risk*100); document.getElementById("voice-risk-score").textContent = risk.toFixed(2); updateChartData(charts.dashAudio, risk*100);
        document.getElementById("voice-alert-badge").textContent = data.level || "NONE";
      } catch (e) {}
    }

    async function checkStatus() { try { const r = await fetch("/status"); const data = await r.json(); if (data.model_loaded) { document.getElementById("model-dot").className="dot"; document.getElementById("model-status").textContent="System Active"; } if (data.camera_ok) { document.getElementById("cam-dot").style.background="var(--success)"; } } catch (e) { } }

    async function pollFaceVerifyStatus() {
      try {
        const r = await fetch("/face_verify_status"); const d = await r.json();
        document.getElementById("face-sim-val").textContent = d.similarity ? (d.similarity*100).toFixed(1)+'%' : "—";
        document.getElementById("face-live-val").textContent = d.liveness_label || "—";
        const badge = document.getElementById("face-match-badge");
        if (d.liveness_label === "No Face") {
          badge.textContent = "UNVERIFIED"; badge.style.color = "var(--text-secondary)";
          document.getElementById('hud-face').textContent = 'NO'; document.getElementById('hud-face').style.color='var(--danger)';
          document.getElementById('foot-face').textContent = 'No'; document.getElementById('foot-face').style.color='var(--danger)';
        } else if (d.match) {
          badge.innerHTML = "VERIFIED ✓"; badge.style.color = "var(--success)";
          document.getElementById("face-name-val").textContent = d.driver_name;
          document.getElementById('hud-id').textContent = 'VERIFIED'; document.getElementById('hud-id').style.color='var(--success)';
          document.getElementById('hud-face').textContent = 'DETECTED'; document.getElementById('hud-face').style.color='var(--success)';
          document.getElementById('foot-face').textContent = 'Yes'; document.getElementById('foot-face').style.color='var(--success)';
          document.getElementById('foot-id').textContent = (d.similarity).toFixed(2);
        } else { badge.textContent = "UNRECOGNIZED"; badge.style.color = "var(--warning)"; }
        document.getElementById('hud-live').textContent = d.liveness_label; document.getElementById('foot-live').textContent = d.liveness_score ? d.liveness_score.toFixed(2) : '0.0';
      } catch(e){}
    }

    function openEnrolModal() { document.getElementById("enrol-overlay").classList.add("visible"); } function closeEnrolModal() { document.getElementById("enrol-overlay").classList.remove("visible"); }
    function openFaceEnrolModal() { document.getElementById("face-enrol-overlay").classList.add("visible"); } function closeFaceEnrolModal() { document.getElementById("face-enrol-overlay").classList.remove("visible"); }
    
    checkStatus(); setInterval(checkStatus, 8000); connectSSE(); connectAudioSSE(); setInterval(pollVoiceResults, 1000); setInterval(pollFaceVerifyStatus, 1000);
  </script>
</body>
</html>
"""

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Done generating templates/index.html")
