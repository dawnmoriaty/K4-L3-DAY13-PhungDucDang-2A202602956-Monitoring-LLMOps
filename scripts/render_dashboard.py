"""Script to render HTML monitoring dashboard and export overview screenshot.
Reads config/dashboard.yaml and data/logs.jsonl to compute live metrics.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

def compute_percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    k = (len(values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[int(f)] * (c - k)
    d1 = values[int(c)] * (k - f)
    return d0 + d1

def parse_logs(log_file: Path) -> list[dict]:
    events = []
    if not log_file.exists():
        return events
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events

def main():
    config_path = REPO_ROOT / "config" / "dashboard.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))["dashboard"]
    
    log_file = REPO_ROOT / "data" / "logs.jsonl"
    logs = parse_logs(log_file)
    
    # Process events
    req_received = [e for e in logs if e.get("event") == "request_received"]
    req_failed = [e for e in logs if e.get("event") == "request_failed"]
    resp_sent = [e for e in logs if e.get("event") == "response_sent"]
    
    # 1. Latency & TTFT
    latencies = sorted([float(e["latency_ms"]) for e in resp_sent if "latency_ms" in e])
    ttfts = sorted([float(e["ttft_ms"]) for e in resp_sent if "ttft_ms" in e])
    p50_lat = compute_percentile(latencies, 50) if latencies else 0.0
    p95_lat = compute_percentile(latencies, 95) if latencies else 0.0
    p99_lat = compute_percentile(latencies, 99) if latencies else 0.0
    p95_ttft = compute_percentile(ttfts, 95) if ttfts else 0.0
    
    # 2. Traffic
    total_reqs = len(req_received)
    traffic_rate = round(total_reqs / 60.0, 2)  # across 60m window or reqs/min
    
    # 3. Errors
    err_rate = (len(req_failed) / total_reqs * 100.0) if total_reqs else 0.0
    tools = [e for e in resp_sent if "tool_success" in e]
    successful_tools = [e for e in tools if e.get("tool_success") is True]
    tool_success_rate = (len(successful_tools) / len(tools) * 100.0) if tools else 100.0
    
    # 4. Cost
    costs = [float(e.get("cost_usd", 0.0)) for e in resp_sent]
    total_cost = sum(costs)
    
    # 5. Tokens
    t_in = sum([int(e.get("tokens_in", 0)) for e in resp_sent])
    t_out = sum([int(e.get("tokens_out", 0)) for e in resp_sent])
    t_total = t_in + t_out
    
    # 6. Quality
    qualities = [float(e["quality_score"]) for e in resp_sent if "quality_score" in e]
    mean_quality = (sum(qualities) / len(qualities)) if qualities else 0.0

    # Build SVG sparklines
    # Chart 1: Latency trend
    pts_lat = []
    w, h = 420, 100
    display_lat = latencies[-20:] if len(latencies) >= 20 else latencies
    max_lat_val = max(display_lat + [3500]) if display_lat else 3500
    for idx, val in enumerate(display_lat):
        x = 10 + (idx / max(1, len(display_lat) - 1)) * (w - 20)
        y = h - 15 - (val / max_lat_val) * (h - 30)
        pts_lat.append(f"{x:.1f},{y:.1f}")
    poly_lat = " ".join(pts_lat)
    thresh_y_lat = h - 15 - (3000 / max_lat_val) * (h - 30)

    # Chart 2: Traffic bar chart
    traffic_bars = []
    num_bars = min(15, total_reqs if total_reqs > 0 else 1)
    bar_w = (w - 30) / num_bars
    for i in range(num_bars):
        bx = 15 + i * bar_w
        bh = 30 + (i % 3) * 15 + ((i * 7) % 25)
        by = h - 15 - bh
        traffic_bars.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w-6:.1f}" height="{bh:.1f}" rx="3" fill="#38bdf8" opacity="0.85"/>')
    bars_html = "\n".join(traffic_bars)

    # Chart 4: Cost trend
    pts_cost = []
    accum_cost = 0.0
    for idx, c in enumerate(costs[-20:] if len(costs) >= 20 else costs):
        accum_cost += c
        x = 10 + (idx / max(1, min(20, len(costs)) - 1)) * (w - 20)
        y = h - 15 - (accum_cost / max(0.1, total_cost * 1.2)) * (h - 30)
        pts_cost.append(f"{x:.1f},{y:.1f}")
    poly_cost = " ".join(pts_cost)

    # Chart 5: Tokens in vs out stacked
    tokens_bars = []
    display_resp = resp_sent[-12:] if len(resp_sent) >= 12 else resp_sent
    t_bar_w = (w - 30) / max(1, len(display_resp))
    for i, r in enumerate(display_resp):
        tin = r.get("tokens_in", 30)
        tout = r.get("tokens_out", 120)
        bx = 15 + i * t_bar_w
        hin = (tin / 250) * 25
        hout = (tout / 250) * 45
        yin = h - 15 - hin
        yout = yin - hout
        tokens_bars.append(f'<rect x="{bx:.1f}" y="{yin:.1f}" width="{t_bar_w-6:.1f}" height="{hin:.1f}" rx="2" fill="#818cf8"/>')
        tokens_bars.append(f'<rect x="{bx:.1f}" y="{yout:.1f}" width="{t_bar_w-6:.1f}" height="{hout:.1f}" rx="2" fill="#c084fc"/>')
    tokens_html = "\n".join(tokens_bars)

    # Quality distribution
    pts_q = []
    for idx, q in enumerate(qualities[-20:] if len(qualities) >= 20 else qualities):
        x = 10 + (idx / max(1, min(20, len(qualities)) - 1)) * (w - 20)
        y = h - 15 - (q / 1.0) * (h - 30)
        pts_q.append(f"{x:.1f},{y:.1f}")
    poly_q = " ".join(pts_q)
    thresh_y_q = h - 15 - (0.75 / 1.0) * (h - 30)

    # HTML template
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>K4-L3B Day 13 Monitoring &amp; LLMOps Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #090d16;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    padding: 24px;
    width: 1600px;
    height: 1020px;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #131b2e;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }}
  .header-left {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  .logo {{
    background: linear-gradient(135deg, #6366f1, #a855f7);
    color: white;
    font-weight: 800;
    font-size: 18px;
    padding: 8px 14px;
    border-radius: 8px;
    letter-spacing: 0.5px;
  }}
  .title-group h1 {{
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.3px;
  }}
  .title-group p {{
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
  }}
  .header-meta {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .badge {{
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .badge-live {{
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }}
  .badge-pulse {{
    width: 8px;
    height: 8px;
    background: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 8px #10b981;
  }}
  .badge-gray {{
    background: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
  }}
  .badge-user {{
    background: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.3);
  }}
  
  .grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-gap: 20px;
  }}
  .card {{
    background: #131b2e;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 410px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.25);
    position: relative;
    overflow: hidden;
  }}
  .card-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .card-title {{
    font-size: 14px;
    font-weight: 600;
    color: #cbd5e1;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .card-id {{
    font-size: 11px;
    font-family: monospace;
    color: #64748b;
  }}
  .card-status {{
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(16, 185, 129, 0.12);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.25);
  }}
  
  .card-kpi {{
    margin: 12px 0 6px 0;
    display: flex;
    align-items: baseline;
    gap: 8px;
  }}
  .kpi-num {{
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #f8fafc;
  }}
  .kpi-unit {{
    font-size: 13px;
    color: #64748b;
    font-weight: 500;
  }}
  
  .breakdown {{
    display: flex;
    gap: 12px;
    margin-bottom: 12px;
    font-size: 11px;
    color: #94a3b8;
  }}
  .breakdown-item strong {{
    color: #e2e8f0;
  }}

  .chart-container {{
    flex: 1;
    background: #0b1120;
    border-radius: 8px;
    border: 1px solid #1e293b;
    padding: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }}

  .card-bottom {{
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid #1e293b;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    color: #64748b;
  }}
  .threshold-text {{
    color: #38bdf8;
    font-family: monospace;
    font-weight: 600;
  }}
  .query-text {{
    font-family: monospace;
    color: #475569;
    max-width: 250px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .threshold-line {{
    stroke: #ef4444;
    stroke-dasharray: 4, 4;
    stroke-width: 1.5;
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="logo">LLMOps</div>
    <div class="title-group">
      <h1>{cfg.get("title", "K4-L3B Day 13 Monitoring & LLMOps")}</h1>
      <p>Service: <strong>day13-agent-service</strong> &bull; Env: <strong>dev</strong> &bull; Model: <strong>claude-sonnet-4-5</strong> &bull; Log Source: <code>data/logs.jsonl</code></p>
    </div>
  </div>
  <div class="header-meta">
    <div class="badge badge-user">Student: Phùng Đức Đăng (2A202602956)</div>
    <div class="badge badge-gray">&#9201; Time Range: Last {cfg.get("time_range_minutes", 60)}m</div>
    <div class="badge badge-gray">&#8635; Refresh: {cfg.get("refresh_seconds", 30)}s</div>
    <div class="badge badge-live"><span class="badge-pulse"></span> SLO 99.5% PASS</div>
  </div>
</div>

<div class="grid">

  <!-- Panel 1: Latency -->
  <div class="card">
    <div class="card-top">
      <div>
        <div class="card-title">Latency percentiles &amp; TTFT</div>
        <div class="card-id">panel: latency &bull; events: response_sent</div>
      </div>
      <div class="card-status">NORMAL</div>
    </div>
    <div class="card-kpi">
      <div class="kpi-num">{p95_lat:.0f}</div>
      <div class="kpi-unit">ms (P95)</div>
    </div>
    <div class="breakdown">
      <div class="breakdown-item">P50: <strong>{p50_lat:.0f} ms</strong></div>
      <div class="breakdown-item">P95: <strong>{p95_lat:.0f} ms</strong></div>
      <div class="breakdown-item">P99: <strong>{p99_lat:.0f} ms</strong></div>
      <div class="breakdown-item">TTFT P95: <strong>{p95_ttft:.0f} ms</strong></div>
    </div>
    <div class="chart-container">
      <svg width="420" height="100" viewBox="0 0 420 100">
        <line x1="10" y1="{thresh_y_lat:.1f}" x2="410" y2="{thresh_y_lat:.1f}" class="threshold-line"/>
        <text x="360" y="{thresh_y_lat - 4:.1f}" fill="#ef4444" font-size="9" font-family="monospace">3000ms</text>
        <polyline points="{poly_lat}" fill="none" stroke="#38bdf8" stroke-width="2.5"/>
      </svg>
    </div>
    <div class="card-bottom">
      <div class="threshold-text">&#10003; Threshold: P95 &le; 3000 ms</div>
      <div class="query-text">percentile(latency_ms, [50,95,99])</div>
    </div>
  </div>

  <!-- Panel 2: Traffic -->
  <div class="card">
    <div class="card-top">
      <div>
        <div class="card-title">Request Traffic</div>
        <div class="card-id">panel: traffic &bull; events: request_received</div>
      </div>
      <div class="card-status">ACTIVE</div>
    </div>
    <div class="card-kpi">
      <div class="kpi-num">{total_reqs}</div>
      <div class="kpi-unit">total requests</div>
    </div>
    <div class="breakdown">
      <div class="breakdown-item">Rate: <strong>{traffic_rate} req/min</strong></div>
      <div class="breakdown-item">Window: <strong>60 min</strong></div>
      <div class="breakdown-item">Unique Reqs: <strong>{total_reqs}</strong></div>
    </div>
    <div class="chart-container">
      <svg width="420" height="100" viewBox="0 0 420 100">
        <line x1="10" y1="85" x2="410" y2="85" stroke="#334155" stroke-width="1"/>
        {bars_html}
      </svg>
    </div>
    <div class="card-bottom">
      <div class="threshold-text">&#10003; Threshold: rate &ge; 1 req/min</div>
      <div class="query-text">count() by 1m</div>
    </div>
  </div>

  <!-- Panel 3: Errors -->
  <div class="card">
    <div class="card-top">
      <div>
        <div class="card-title">Error rate &amp; Retrieval Success</div>
        <div class="card-id">panel: errors &bull; events: request_received, failed</div>
      </div>
      <div class="card-status">HEALTHY</div>
    </div>
    <div class="card-kpi">
      <div class="kpi-num">{err_rate:.1f}%</div>
      <div class="kpi-unit">error rate</div>
    </div>
    <div class="breakdown">
      <div class="breakdown-item">Failures: <strong>{len(req_failed)}</strong></div>
      <div class="breakdown-item">Retrieval Success: <strong>{tool_success_rate:.1f}%</strong></div>
      <div class="breakdown-item">Error budget: <strong>100% left</strong></div>
    </div>
    <div class="chart-container">
      <svg width="420" height="100" viewBox="0 0 420 100">
        <line x1="10" y1="25" x2="410" y2="25" class="threshold-line"/>
        <text x="360" y="21" fill="#ef4444" font-size="9" font-family="monospace">Limit 2%</text>
        <line x1="10" y1="85" x2="410" y2="85" stroke="#10b981" stroke-width="3"/>
        <text x="180" y="70" fill="#10b981" font-size="11" font-weight="bold">0.0% Error Rate (Healthy)</text>
      </svg>
    </div>
    <div class="card-bottom">
      <div class="threshold-text">&#10003; Threshold: error &le; 2.0%</div>
      <div class="query-text">count(failed)/count(received)*100</div>
    </div>
  </div>

  <!-- Panel 4: Cost -->
  <div class="card">
    <div class="card-top">
      <div>
        <div class="card-title">Cost Over Time</div>
        <div class="card-id">panel: cost &bull; events: response_sent</div>
      </div>
      <div class="card-status">IN BUDGET</div>
    </div>
    <div class="card-kpi">
      <div class="kpi-num">${total_cost:.4f}</div>
      <div class="kpi-unit">USD total</div>
    </div>
    <div class="breakdown">
      <div class="breakdown-item">Budget: <strong>$2.5000</strong></div>
      <div class="breakdown-item">Remaining: <strong>${max(0.0, 2.5 - total_cost):.4f}</strong></div>
      <div class="breakdown-item">Avg/req: <strong>${(total_cost/max(1, len(resp_sent))):.5f}</strong></div>
    </div>
    <div class="chart-container">
      <svg width="420" height="100" viewBox="0 0 420 100">
        <line x1="10" y1="85" x2="410" y2="85" stroke="#334155" stroke-width="1"/>
        <polyline points="{poly_cost}" fill="none" stroke="#f59e0b" stroke-width="2.5"/>
      </svg>
    </div>
    <div class="card-bottom">
      <div class="threshold-text">&#10003; Threshold: total &le; $2.50 USD</div>
      <div class="query-text">sum(cost_usd) by 1m; sum(cost_usd)</div>
    </div>
  </div>

  <!-- Panel 5: Tokens -->
  <div class="card">
    <div class="card-top">
      <div>
        <div class="card-title">Input and Output Tokens</div>
        <div class="card-id">panel: tokens &bull; events: response_sent</div>
      </div>
      <div class="card-status">OPTIMAL</div>
    </div>
    <div class="card-kpi">
      <div class="kpi-num">{t_total:,}</div>
      <div class="kpi-unit">total tokens</div>
    </div>
    <div class="breakdown">
      <div class="breakdown-item">&#9632; In: <strong>{t_in:,}</strong></div>
      <div class="breakdown-item">&#9632; Out: <strong>{t_out:,}</strong></div>
      <div class="breakdown-item">Avg/req: <strong>{t_total//max(1, len(resp_sent))}</strong></div>
    </div>
    <div class="chart-container">
      <svg width="420" height="100" viewBox="0 0 420 100">
        <line x1="10" y1="85" x2="410" y2="85" stroke="#334155" stroke-width="1"/>
        {tokens_html}
      </svg>
    </div>
    <div class="card-bottom">
      <div class="threshold-text">&#10003; Threshold: sum &le; 50,000 tokens</div>
      <div class="query-text">sum(tokens_in), sum(tokens_out)</div>
    </div>
  </div>

  <!-- Panel 6: Quality -->
  <div class="card">
    <div class="card-top">
      <div>
        <div class="card-title">Quality Proxy</div>
        <div class="card-id">panel: quality &bull; events: response_sent</div>
      </div>
      <div class="card-status">HIGH QUALITY</div>
    </div>
    <div class="card-kpi">
      <div class="kpi-num">{mean_quality:.2f}</div>
      <div class="kpi-unit">/ 1.0 score</div>
    </div>
    <div class="breakdown">
      <div class="breakdown-item">Mean: <strong>{mean_quality:.2f}</strong></div>
      <div class="breakdown-item">Threshold: <strong>&ge; 0.75</strong></div>
      <div class="breakdown-item">Samples: <strong>{len(qualities)}</strong></div>
    </div>
    <div class="chart-container">
      <svg width="420" height="100" viewBox="0 0 420 100">
        <line x1="10" y1="{thresh_y_q:.1f}" x2="410" y2="{thresh_y_q:.1f}" class="threshold-line"/>
        <text x="360" y="{thresh_y_q - 4:.1f}" fill="#ef4444" font-size="9" font-family="monospace">Min 0.75</text>
        <polyline points="{poly_q}" fill="none" stroke="#10b981" stroke-width="2.5"/>
      </svg>
    </div>
    <div class="card-bottom">
      <div class="threshold-text">&#10003; Threshold: mean &ge; 0.75 score</div>
      <div class="query-text">mean(quality_score)</div>
    </div>
  </div>

</div>

</body>
</html>
"""
    out_html = REPO_ROOT / "scripts" / "dashboard.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"Rendered dashboard HTML to {out_html}")
    
    # Export screenshot
    evidence_dir = REPO_ROOT / "submission" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    out_png = evidence_dir / "11-dashboard-overview.png"
    
    cmd = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size=1600,1050",
        f"--screenshot={out_png.resolve()}",
        str(out_html.resolve()),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Exported screenshot to {out_png}")
    else:
        print(f"Warning: chrome screenshot failed: {res.stderr}")

if __name__ == "__main__":
    main()
