#!/usr/bin/env python3
"""
Generate an HTML ASCII video player from an mp4 file.
Extracts frames, converts to ASCII art (matching tplay's CHARS3), 
and creates an animated HTML player with controls.
"""

import subprocess, sys, os, json
from PIL import Image

CHARS3 = " `.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu[neoZ5Yxjya]2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
ASCII_WIDTH = 120
ASCII_HEIGHT = 40
TARGET_FPS = 12  # smooth animation

def build_lut(char_map):
    lut = [' '] * 256
    length = len(char_map)
    for i in range(256):
        lut[i] = char_map[length * i // 256]
    return lut

def frame_to_ascii(img, lut, width, height):
    img_resized = img.resize((width, height), Image.LANCZOS)
    img_rgb = img_resized.convert('RGB')
    pixels = img_rgb.load()
    lines = []
    for y in range(height):
        row = []
        for x in range(width):
            r, g, b = pixels[x, y]
            lum = min((r * 2126 + g * 7152 + b * 722) // 10000, 255)
            row.append(lut[lum])
        lines.append(''.join(row))
    return '\n'.join(lines)

def extract_frames(video_path, fps):
    probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', video_path]
    probe_data = json.loads(subprocess.run(probe_cmd, capture_output=True, text=True).stdout)
    vs = [s for s in probe_data['streams'] if s['codec_type'] == 'video'][0]
    orig_w, orig_h = int(vs['width']), int(vs['height'])
    scale_w = 320
    scale_h = int(orig_h * scale_w / orig_w)
    scale_h += scale_h % 2
    cmd = ['ffmpeg', '-i', video_path, '-vf', f'fps={fps},scale={scale_w}:{scale_h}',
           '-f', 'image2pipe', '-pix_fmt', 'rgb24', '-vcodec', 'rawvideo', '-v', 'quiet', '-']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frames = []
    frame_size = scale_w * scale_h * 3
    while True:
        raw = process.stdout.read(frame_size)
        if len(raw) < frame_size:
            break
        frames.append(Image.frombytes('RGB', (scale_w, scale_h), raw))
    process.wait()
    return frames

def generate_html(ascii_frames, fps, output_path):
    # Escape frames for JS
    escaped = []
    for f in ascii_frames:
        escaped.append(f.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$'))
    
    frames_js = ',\n'.join(f'`{f}`' for f in escaped)
    total = len(ascii_frames)
    duration = total / fps

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASCII Video Player — me2.mp4</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: #0a0a0f;
  color: #e0e0e0;
  font-family: 'JetBrains Mono', monospace;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
}}
h1 {{
  font-size: 1.4rem;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #00f5a0, #00d9f5);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}}
.player-wrapper {{
  background: #111118;
  border: 1px solid #1e1e2e;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 0 40px rgba(0, 245, 160, 0.05), 0 0 80px rgba(0, 0, 0, 0.5);
  max-width: 95vw;
  overflow: hidden;
}}
.title-bar {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #1e1e2e;
}}
.dot {{ width: 12px; height: 12px; border-radius: 50%; }}
.dot.r {{ background: #ff5f57; }}
.dot.y {{ background: #febc2e; }}
.dot.g {{ background: #28c840; }}
.title-bar span {{
  margin-left: 12px;
  font-size: 0.75rem;
  color: #555;
}}
#screen {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 8.5px;
  line-height: 1.1;
  white-space: pre;
  color: #00f5a0;
  background: #05050a;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #1a1a2a;
  overflow: hidden;
  min-height: 350px;
  text-shadow: 0 0 2px rgba(0, 245, 160, 0.3);
  transition: color 0.3s;
}}
.controls {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  flex-wrap: wrap;
}}
.controls button {{
  background: #1a1a2a;
  color: #00f5a0;
  border: 1px solid #2a2a3a;
  border-radius: 6px;
  padding: 8px 14px;
  font-family: inherit;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}}
.controls button:hover {{
  background: #00f5a0;
  color: #0a0a0f;
  box-shadow: 0 0 12px rgba(0, 245, 160, 0.3);
}}
.controls button.active {{
  background: #00f5a0;
  color: #0a0a0f;
}}
.progress-container {{
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
#progress {{
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #1a1a2a;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}}
#progress::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #00f5a0;
  box-shadow: 0 0 6px rgba(0, 245, 160, 0.5);
  cursor: pointer;
}}
#progress::-moz-range-thumb {{
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #00f5a0;
  border: none;
  cursor: pointer;
}}
#progress::-webkit-slider-runnable-track {{
  height: 6px;
  border-radius: 3px;
}}
.info {{
  font-size: 0.7rem;
  color: #555;
  white-space: nowrap;
}}
.speed-group {{
  display: flex;
  gap: 4px;
}}
.color-group {{
  display: flex;
  gap: 4px;
}}
.color-btn {{
  width: 20px !important;
  height: 20px !important;
  padding: 0 !important;
  border-radius: 50% !important;
  min-width: 20px;
}}
.footer {{
  margin-top: 16px;
  font-size: 0.65rem;
  color: #333;
  text-align: center;
}}
</style>
</head>
<body>

<h1>▶ ASCII VIDEO PLAYER</h1>

<div class="player-wrapper">
  <div class="title-bar">
    <div class="dot r"></div>
    <div class="dot y"></div>
    <div class="dot g"></div>
    <span>me2.mp4 — {total} frames @ {fps}fps — tplay CHARS3</span>
  </div>

  <div id="screen">Loading...</div>

  <div class="controls">
    <button id="playBtn" onclick="togglePlay()">▶ Play</button>
    <button onclick="stepBack()">⏮</button>
    <button onclick="stepForward()">⏭</button>

    <div class="progress-container">
      <span class="info" id="timeInfo">0:00</span>
      <input type="range" id="progress" min="0" max="{total - 1}" value="0">
      <span class="info" id="durInfo">{duration:.1f}s</span>
    </div>

    <div class="speed-group">
      <button onclick="setSpeed(0.25)">¼×</button>
      <button onclick="setSpeed(0.5)">½×</button>
      <button class="active" id="speed1" onclick="setSpeed(1)">1×</button>
      <button onclick="setSpeed(2)">2×</button>
    </div>

    <div class="color-group">
      <button class="color-btn" style="background:#00f5a0" onclick="setColor('#00f5a0')"></button>
      <button class="color-btn" style="background:#00d9f5" onclick="setColor('#00d9f5')"></button>
      <button class="color-btn" style="background:#f5a000" onclick="setColor('#f5a000')"></button>
      <button class="color-btn" style="background:#e0e0e0" onclick="setColor('#e0e0e0')"></button>
    </div>

    <button id="loopBtn" onclick="toggleLoop()">🔁 Off</button>
  </div>
</div>

<div class="footer">
  Generated from me2.mp4 using tplay-style ASCII conversion (CHARS3, BT.709 luminance)
</div>

<script>
const frames = [
{frames_js}
];

const FPS = {fps};
let currentFrame = 0;
let playing = false;
let speed = 1;
let looping = false;
let intervalId = null;
const screen = document.getElementById('screen');
const progress = document.getElementById('progress');
const playBtn = document.getElementById('playBtn');
const timeInfo = document.getElementById('timeInfo');
const loopBtn = document.getElementById('loopBtn');

function render() {{
  screen.textContent = frames[currentFrame];
  progress.value = currentFrame;
  const sec = currentFrame / FPS;
  const m = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(1);
  timeInfo.textContent = m + ':' + (s < 10 ? '0' : '') + s;
}}

function togglePlay() {{
  playing = !playing;
  playBtn.textContent = playing ? '⏸ Pause' : '▶ Play';
  if (playing) startInterval();
  else stopInterval();
}}

function startInterval() {{
  stopInterval();
  intervalId = setInterval(() => {{
    currentFrame++;
    if (currentFrame >= frames.length) {{
      if (looping) {{ currentFrame = 0; }}
      else {{ currentFrame = frames.length - 1; playing = false; playBtn.textContent = '▶ Play'; stopInterval(); }}
    }}
    render();
  }}, 1000 / (FPS * speed));
}}

function stopInterval() {{
  if (intervalId) {{ clearInterval(intervalId); intervalId = null; }}
}}

function stepForward() {{
  if (currentFrame < frames.length - 1) currentFrame++;
  render();
}}

function stepBack() {{
  if (currentFrame > 0) currentFrame--;
  render();
}}

function setSpeed(s) {{
  speed = s;
  document.querySelectorAll('.speed-group button').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  if (playing) startInterval();
}}

function setColor(c) {{
  screen.style.color = c;
  screen.style.textShadow = '0 0 2px ' + c + '4d';
}}

function toggleLoop() {{
  looping = !looping;
  loopBtn.textContent = looping ? '🔁 On' : '🔁 Off';
  if (looping) loopBtn.classList.add('active');
  else loopBtn.classList.remove('active');
}}

progress.addEventListener('input', () => {{
  currentFrame = parseInt(progress.value);
  render();
}});

document.addEventListener('keydown', (e) => {{
  if (e.code === 'Space') {{ e.preventDefault(); togglePlay(); }}
  else if (e.code === 'ArrowRight') stepForward();
  else if (e.code === 'ArrowLeft') stepBack();
}});

render();
</script>
</body>
</html>'''

    with open(output_path, 'w') as f:
        f.write(html)

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    video_path = os.path.join(base, 'me2.mp4')
    output_path = os.path.join(base, 'PLAY.html')

    print(f"Extracting frames at {TARGET_FPS} fps...")
    frames = extract_frames(video_path, TARGET_FPS)
    print(f"Extracted {len(frames)} frames")

    lut = build_lut(CHARS3)
    ascii_frames = []
    for i, frame in enumerate(frames):
        ascii_frames.append(frame_to_ascii(frame, lut, ASCII_WIDTH, ASCII_HEIGHT))
        if (i + 1) % 10 == 0:
            print(f"  Converted {i+1}/{len(frames)}")
    print(f"  Converted {len(frames)}/{len(frames)}")

    print("Generating HTML player...")
    generate_html(ascii_frames, TARGET_FPS, output_path)
    print(f"Done! Open {output_path} in your browser.")

if __name__ == '__main__':
    main()
