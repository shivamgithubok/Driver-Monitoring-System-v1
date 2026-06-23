import re

with open('generate_ui.py', 'r') as f:
    content = f.read()

# Make view-container fit
content = content.replace("overflow-y: auto; animation: fadeIn 0.3s ease;", "overflow: hidden; animation: fadeIn 0.3s ease; padding: 12px; gap: 12px;")

# Modify body to ensure 100vh
content = content.replace("height: 100vh; display: flex; overflow: hidden;", "height: 100vh; width: 100vw; display: flex; overflow: hidden; padding: 0;")

# We'll completely rewrite the dashboard HTML layout using regex
dashboard_html = """      <!-- DASHBOARD -->
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
                <div class="id-avatar"><img src="/static/avatar-placeholder.png" alt="" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 24 24\\' fill=\\'%23fff\\'%3E%3Cpath d=\\'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z\\'/%3E%3C/svg%3E';"><div class="id-badge">✓</div></div>
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
      </div>"""

# Replace the middle part
content = re.sub(r'<!-- DASHBOARD -->.*?<!-- LIVE MONITORING -->', dashboard_html + "\n\n      <!-- LIVE MONITORING -->", content, flags=re.DOTALL)

with open('generate_ui.py', 'w') as f:
    f.write(content)

print("Patching complete.")
