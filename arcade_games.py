"""Self-contained, offline HTML5 arcade games for Lumen Orbit.

All games run 100% locally in the browser with zero external network dependencies,
zero iframe restrictions, and zero CSP issues.
"""

from __future__ import annotations


def get_2048_html(theme_primary: str = "#6366F1", theme_bg: str = "#0F172A") -> str:
    """Return self-contained HTML5 2048 game."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>2048 Arcade</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; -webkit-user-select: none; }}
  body {{
    background: {theme_bg};
    color: #F8FAFC;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 12px;
  }}
  .game-container {{
    width: 100%;
    max-width: 440px;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }}
  .title {{
    font-size: 2.2rem;
    font-weight: 900;
    letter-spacing: -1px;
    background: linear-gradient(135deg, {theme_primary}, #38BDF8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .scores {{
    display: flex;
    gap: 8px;
  }}
  .score-box {{
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 6px 14px;
    text-align: center;
    min-width: 70px;
  }}
  .score-label {{
    font-size: 0.65rem;
    text-transform: uppercase;
    color: #94A3B8;
    font-weight: 700;
  }}
  .score-val {{
    font-size: 1.15rem;
    font-weight: 800;
    color: #F8FAFC;
  }}
  .controls {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
  }}
  .subtitle {{
    font-size: 0.82rem;
    color: #94A3B8;
  }}
  .btn-group {{
    display: flex;
    gap: 6px;
  }}
  .btn {{
    background: {theme_primary};
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.1s, opacity 0.2s;
  }}
  .btn:hover {{ opacity: 0.9; transform: translateY(-1px); }}
  .btn:active {{ transform: scale(0.96); }}
  .btn-undo {{
    background: rgba(255, 255, 255, 0.1);
    color: #E2E8F0;
  }}
  .grid {{
    width: 100%;
    aspect-ratio: 1;
    background: rgba(15, 23, 42, 0.9);
    border-radius: 12px;
    padding: 10px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    grid-gap: 10px;
    position: relative;
    touch-action: none;
  }}
  .cell {{
    background: rgba(51, 65, 85, 0.4);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.7rem;
    font-weight: 800;
    transition: transform 0.1s ease-in-out;
  }}
  .tile-2    {{ background: #eee4da; color: #776e65; }}
  .tile-4    {{ background: #ede0c8; color: #776e65; }}
  .tile-8    {{ background: #f2b179; color: #f9f6f2; }}
  .tile-16   {{ background: #f59563; color: #f9f6f2; }}
  .tile-32   {{ background: #f67c5f; color: #f9f6f2; }}
  .tile-64   {{ background: #f65e3b; color: #f9f6f2; }}
  .tile-128  {{ background: #edcf72; color: #f9f6f2; font-size: 1.45rem; box-shadow: 0 0 10px rgba(237,207,114,0.5); }}
  .tile-256  {{ background: #edcc61; color: #f9f6f2; font-size: 1.45rem; box-shadow: 0 0 12px rgba(237,204,97,0.6); }}
  .tile-512  {{ background: #edc850; color: #f9f6f2; font-size: 1.45rem; box-shadow: 0 0 15px rgba(237,200,80,0.7); }}
  .tile-1024 {{ background: #edc53f; color: #f9f6f2; font-size: 1.2rem;  box-shadow: 0 0 18px rgba(237,197,63,0.8); }}
  .tile-2048 {{ background: #edc22e; color: #f9f6f2; font-size: 1.2rem;  box-shadow: 0 0 25px rgba(237,194,46,1); }}
  .tile-super{{ background: #3c3a32; color: #f9f6f2; font-size: 1.05rem; }}
  .tile-new  {{ animation: pop 0.15s ease-in-out; }}

  @keyframes pop {{
    0% {{ transform: scale(0); }}
    60% {{ transform: scale(1.12); }}
    100% {{ transform: scale(1); }}
  }}

  .overlay {{
    position: absolute;
    inset: 0;
    background: rgba(15, 23, 42, 0.92);
    border-radius: 12px;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 10;
    gap: 12px;
    backdrop-filter: blur(4px);
  }}
  .overlay.active {{ display: flex; }}
  .overlay-msg {{
    font-size: 1.7rem;
    font-weight: 800;
    color: #F8FAFC;
  }}
  .footer-hints {{
    margin-top: 14px;
    display: flex;
    justify-content: space-between;
    color: #64748B;
    font-size: 0.75rem;
  }}
</style>
</head>
<body>
<div class="game-container">
  <div class="header">
    <div class="title">2048</div>
    <div class="scores">
      <div class="score-box">
        <div class="score-label">Score</div>
        <div class="score-val" id="score">0</div>
      </div>
      <div class="score-box">
        <div class="score-label">Best</div>
        <div class="score-val" id="best">0</div>
      </div>
    </div>
  </div>

  <div class="controls">
    <div class="subtitle">Join tiles to reach <b>2048</b>!</div>
    <div class="btn-group">
      <button class="btn btn-undo" onclick="undoMove()">↩ Undo</button>
      <button class="btn" onclick="initGame()">⚡ New Game</button>
    </div>
  </div>

  <div class="grid" id="grid">
    <div class="overlay" id="overlay">
      <div class="overlay-msg" id="overlayMsg">Game Over!</div>
      <button class="btn" onclick="initGame()" style="padding:10px 24px;font-size:1rem;">Play Again</button>
    </div>
  </div>

  <div class="footer-hints">
    <span>Controls: <b>Arrow Keys</b> or <b>W A S D</b></span>
    <span>Mobile: <b>Swipe</b> to move</span>
  </div>
</div>

<script>
  let grid = [];
  let score = 0;
  let historyStack = [];
  let bestScore = parseInt(localStorage.getItem('lumen_2048_best') || '0', 10);
  document.getElementById('best').innerText = bestScore;

  function initGame() {{
    grid = [
      [0, 0, 0, 0],
      [0, 0, 0, 0],
      [0, 0, 0, 0],
      [0, 0, 0, 0]
    ];
    score = 0;
    historyStack = [];
    document.getElementById('overlay').classList.remove('active');
    addRandomTile();
    addRandomTile();
    render();
  }}

  function addRandomTile() {{
    let empty = [];
    for (let r = 0; r < 4; r++) {{
      for (let c = 0; c < 4; c++) {{
        if (grid[r][c] === 0) empty.push({{ r, c }});
      }}
    }}
    if (empty.length === 0) return;
    let spot = empty[Math.floor(Math.random() * empty.length)];
    grid[spot.r][spot.c] = Math.random() < 0.9 ? 2 : 4;
  }}

  function render() {{
    let gridEl = document.getElementById('grid');
    let overlay = document.getElementById('overlay');
    gridEl.innerHTML = '';
    gridEl.appendChild(overlay);

    for (let r = 0; r < 4; r++) {{
      for (let c = 0; c < 4; c++) {{
        let val = grid[r][c];
        let cell = document.createElement('div');
        cell.className = 'cell';
        if (val > 0) {{
          cell.innerText = val;
          cell.classList.add(val <= 2048 ? 'tile-' + val : 'tile-super');
        }}
        gridEl.appendChild(cell);
      }}
    }}
    document.getElementById('score').innerText = score;
    if (score > bestScore) {{
      bestScore = score;
      localStorage.setItem('lumen_2048_best', bestScore.toString());
      document.getElementById('best').innerText = bestScore;
    }}
  }}

  function slide(row) {{
    let arr = row.filter(x => x !== 0);
    for (let i = 0; i < arr.length - 1; i++) {{
      if (arr[i] === arr[i + 1]) {{
        arr[i] *= 2;
        score += arr[i];
        arr[i + 1] = 0;
      }}
    }}
    arr = arr.filter(x => x !== 0);
    while (arr.length < 4) arr.push(0);
    return arr;
  }}

  function rotateLeft(mat) {{
    let res = [[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]];
    for (let r = 0; r < 4; r++) {{
      for (let c = 0; c < 4; c++) {{
        res[3 - c][r] = mat[r][c];
      }}
    }}
    return res;
  }}

  function move(dir) {{
    let prev = JSON.stringify(grid);
    let prevScore = score;

    let rotCount = 0;
    if (dir === 'left')  rotCount = 0;
    if (dir === 'down')  rotCount = 1;
    if (dir === 'right') rotCount = 2;
    if (dir === 'up')    rotCount = 3;

    let work = JSON.parse(prev);
    for (let i = 0; i < rotCount; i++) work = rotateLeft(work);

    for (let r = 0; r < 4; r++) {{
      work[r] = slide(work[r]);
    }}

    for (let i = 0; i < (4 - rotCount) % 4; i++) work = rotateLeft(work);

    if (JSON.stringify(work) !== prev) {{
      historyStack.push({{ grid: JSON.parse(prev), score: prevScore }});
      if (historyStack.length > 20) historyStack.shift();
      grid = work;
      addRandomTile();
      render();
      checkGameOver();
    }}
  }}

  function undoMove() {{
    if (historyStack.length === 0) return;
    let last = historyStack.pop();
    grid = last.grid;
    score = last.score;
    document.getElementById('overlay').classList.remove('active');
    render();
  }}

  function checkGameOver() {{
    for (let r = 0; r < 4; r++) {{
      for (let c = 0; c < 4; c++) {{
        if (grid[r][c] === 0) return;
        if (c < 3 && grid[r][c] === grid[r][c + 1]) return;
        if (r < 3 && grid[r][c] === grid[r + 1][c]) return;
      }}
    }}
    document.getElementById('overlayMsg').innerText = 'Game Over!';
    document.getElementById('overlay').classList.add('active');
  }}

  window.addEventListener('keydown', function(e) {{
    if (['ArrowUp', 'KeyW'].includes(e.code)) {{ e.preventDefault(); move('up'); }}
    else if (['ArrowDown', 'KeyS'].includes(e.code)) {{ e.preventDefault(); move('down'); }}
    else if (['ArrowLeft', 'KeyA'].includes(e.code)) {{ e.preventDefault(); move('left'); }}
    else if (['ArrowRight', 'KeyD'].includes(e.code)) {{ e.preventDefault(); move('right'); }}
  }});

  let touchStartX = 0, touchStartY = 0;
  let gridEl = document.getElementById('grid');
  gridEl.addEventListener('touchstart', function(e) {{
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }}, {{ passive: true }});

  gridEl.addEventListener('touchend', function(e) {{
    let dx = e.changedTouches[0].clientX - touchStartX;
    let dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) < 25 && Math.abs(dy) < 25) return;
    if (Math.abs(dx) > Math.abs(dy)) {{
      move(dx > 0 ? 'right' : 'left');
    }} else {{
      move(dy > 0 ? 'down' : 'up');
    }}
  }}, {{ passive: true }});

  initGame();
</script>
</body>
</html>"""


def get_snake_html(theme_primary: str = "#10B981", theme_bg: str = "#0F172A") -> str:
    """Return self-contained HTML5 Retro Snake game."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Retro Snake</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
  body {{
    background: {theme_bg};
    color: #F8FAFC;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 12px;
  }}
  .card {{
    width: 100%;
    max-width: 440px;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .header {{
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }}
  .title {{
    font-size: 1.8rem;
    font-weight: 900;
    color: {theme_primary};
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .stats {{
    display: flex;
    gap: 10px;
  }}
  .stat-badge {{
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 0.85rem;
    font-weight: 700;
  }}
  canvas {{
    background: #020617;
    border: 2px solid rgba(16, 185, 129, 0.3);
    border-radius: 12px;
    box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
    width: 100%;
    max-width: 400px;
    aspect-ratio: 1;
    display: block;
  }}
  .dpad {{
    display: grid;
    grid-template-columns: repeat(3, 56px);
    grid-template-rows: repeat(2, 46px);
    gap: 6px;
    margin-top: 14px;
    justify-content: center;
  }}
  .dbtn {{
    background: rgba(51, 65, 85, 0.6);
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    font-size: 1.3rem;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }}
  .dbtn:active {{ background: {theme_primary}; }}
  .dbtn-up {{ grid-column: 2; grid-row: 1; }}
  .dbtn-left {{ grid-column: 1; grid-row: 2; }}
  .dbtn-down {{ grid-column: 2; grid-row: 2; }}
  .dbtn-right {{ grid-column: 3; grid-row: 2; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="title">🐍 Snake Retro</div>
    <div class="stats">
      <div class="stat-badge">Score: <span id="score" style="color:#10B981">0</span></div>
      <div class="stat-badge">Best: <span id="best" style="color:#F59E0B">0</span></div>
    </div>
  </div>

  <canvas id="canvas" width="400" height="400"></canvas>

  <div class="dpad">
    <button class="dbtn dbtn-up" onclick="setDir(0, -1)">⬆️</button>
    <button class="dbtn dbtn-left" onclick="setDir(-1, 0)">⬅️</button>
    <button class="dbtn dbtn-down" onclick="setDir(0, 1)">⬇️</button>
    <button class="dbtn dbtn-right" onclick="setDir(1, 0)">➡️</button>
  </div>
</div>

<script>
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  const gridCount = 20;
  const cellSize = canvas.width / gridCount;

  let snake = [{{x: 10, y: 10}}, {{x: 9, y: 10}}, {{x: 8, y: 10}}];
  let food = {{x: 15, y: 10}};
  let dx = 1, dy = 0;
  let nextDx = 1, nextDy = 0;
  let score = 0;
  let best = parseInt(localStorage.getItem('lumen_snake_best') || '0', 10);
  document.getElementById('best').innerText = best;
  let gameInterval = null;

  function spawnFood() {{
    food = {{
      x: Math.floor(Math.random() * gridCount),
      y: Math.floor(Math.random() * gridCount)
    }};
    for (let seg of snake) {{
      if (seg.x === food.x && seg.y === food.y) return spawnFood();
    }}
  }}

  function resetGame() {{
    snake = [{{x: 10, y: 10}}, {{x: 9, y: 10}}, {{x: 8, y: 10}}];
    dx = 1; dy = 0;
    nextDx = 1; nextDy = 0;
    score = 0;
    document.getElementById('score').innerText = score;
    spawnFood();
  }}

  function setDir(nx, ny) {{
    if (nx !== -dx && ny !== -dy) {{
      nextDx = nx;
      nextDy = ny;
    }}
  }}

  window.addEventListener('keydown', e => {{
    if (['ArrowUp', 'KeyW'].includes(e.code)) {{ e.preventDefault(); setDir(0, -1); }}
    else if (['ArrowDown', 'KeyS'].includes(e.code)) {{ e.preventDefault(); setDir(0, 1); }}
    else if (['ArrowLeft', 'KeyA'].includes(e.code)) {{ e.preventDefault(); setDir(-1, 0); }}
    else if (['ArrowRight', 'KeyD'].includes(e.code)) {{ e.preventDefault(); setDir(1, 0); }}
    else if (e.code === 'Space') {{ resetGame(); }}
  }});

  function step() {{
    dx = nextDx;
    dy = nextDy;
    let head = {{x: snake[0].x + dx, y: snake[0].y + dy}};

    // Wall wrap
    if (head.x < 0) head.x = gridCount - 1;
    if (head.x >= gridCount) head.x = 0;
    if (head.y < 0) head.y = gridCount - 1;
    if (head.y >= gridCount) head.y = 0;

    // Self collision
    for (let seg of snake) {{
      if (seg.x === head.x && seg.y === head.y) {{
        resetGame();
        return;
      }}
    }}

    snake.unshift(head);
    if (head.x === food.x && head.y === food.y) {{
      score += 10;
      document.getElementById('score').innerText = score;
      if (score > best) {{
        best = score;
        localStorage.setItem('lumen_snake_best', best.toString());
        document.getElementById('best').innerText = best;
      }}
      spawnFood();
    }} else {{
      snake.pop();
    }}

    // Draw
    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Food
    ctx.fillStyle = '#EF4444';
    ctx.beginPath();
    ctx.arc((food.x + 0.5) * cellSize, (food.y + 0.5) * cellSize, cellSize * 0.45, 0, Math.PI * 2);
    ctx.fill();

    // Snake
    snake.forEach((seg, idx) => {{
      ctx.fillStyle = idx === 0 ? '#34D399' : '#10B981';
      ctx.fillRect(seg.x * cellSize + 1, seg.y * cellSize + 1, cellSize - 2, cellSize - 2);
    }});
  }}

  spawnFood();
  gameInterval = setInterval(step, 110);
</script>
</body>
</html>"""


def get_wordle_html(theme_primary: str = "#6366F1", theme_bg: str = "#0F172A") -> str:
    """Return self-contained HTML5 Wordle Unlimited game."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Wordle Unlimited</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
  body {{
    background: {theme_bg};
    color: #F8FAFC;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 10px;
  }}
  .card {{
    width: 100%;
    max-width: 440px;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .header {{
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }}
  .title {{
    font-size: 1.6rem;
    font-weight: 900;
    color: #10B981;
  }}
  .board {{
    display: grid;
    grid-template-rows: repeat(6, 1fr);
    grid-gap: 6px;
    margin-bottom: 16px;
  }}
  .row {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    grid-gap: 6px;
  }}
  .tile {{
    width: 48px;
    height: 48px;
    border: 2px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
    font-weight: 800;
    text-transform: uppercase;
    background: rgba(15, 23, 42, 0.6);
  }}
  .tile.correct {{ background: #10B981; border-color: #10B981; color: #fff; }}
  .tile.present {{ background: #F59E0B; border-color: #F59E0B; color: #fff; }}
  .tile.absent  {{ background: #334155; border-color: #334155; color: #94A3B8; }}

  .keyboard {{
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .kb-row {{
    display: flex;
    justify-content: center;
    gap: 4px;
  }}
  .key {{
    background: rgba(71, 85, 105, 0.5);
    color: #F8FAFC;
    border: none;
    border-radius: 6px;
    height: 42px;
    padding: 0 10px;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
  }}
  .key.wide {{ padding: 0 14px; font-size: 0.75rem; }}
  .key.correct {{ background: #10B981 !important; }}
  .key.present {{ background: #F59E0B !important; }}
  .key.absent  {{ background: #1E293B !important; color: #64748B; }}

  .banner {{
    margin-top: 10px;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.9rem;
    display: none;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="title">🟩 Wordle Unlimited</div>
    <button onclick="newGame()" style="background:#10B981;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-weight:700;cursor:pointer;">⚡ New Word</button>
  </div>

  <div class="board" id="board"></div>
  <div class="banner" id="banner"></div>

  <div class="keyboard" id="keyboard"></div>
</div>

<script>
  const WORDS = ["APPLE","BEACH","CLOUD","DANCE","EAGLE","FLAME","GRAPE","HEART","IMAGE","JUICE","KNIFE","LEMON","MUSIC","NIGHT","OCEAN","PIANO","QUEEN","RIVER","SMILE","TIGER","UNCLE","VOICE","WATER","YOUTH","ZEBRA","BREAD","CHAIR","DREAM","EARTH","FRUIT","GREEN","HOUSE","LIGHT","MONEY","PLANT","ROUND","SWEET","TRAIN","WORLD","ANGEL","BRAIN","CANDY","DRIVE","FAITH","GHOST","HONEY","JEWEL","MAGIC","NOBLE","PEACE","SHINE","STORM","TOUCH","VALOR","WINGS"];
  let target = "";
  let guesses = [];
  let currentGuess = "";
  let gameOver = false;

  function newGame() {{
    target = WORDS[Math.floor(Math.random() * WORDS.length)];
    guesses = [];
    currentGuess = "";
    gameOver = false;
    document.getElementById('banner').style.display = 'none';
    renderBoard();
    renderKeyboard();
  }}

  function renderBoard() {{
    const board = document.getElementById('board');
    board.innerHTML = '';
    for (let r = 0; r < 6; r++) {{
      let row = document.createElement('div');
      row.className = 'row';
      let word = guesses[r] || (r === guesses.length ? currentGuess : "");
      for (let c = 0; c < 5; c++) {{
        let tile = document.createElement('div');
        tile.className = 'tile';
        let ch = word[c] || "";
        tile.innerText = ch;
        if (r < guesses.length) {{
          if (ch === target[c]) tile.classList.add('correct');
          else if (target.includes(ch)) tile.classList.add('present');
          else tile.classList.add('absent');
        }}
        row.appendChild(tile);
      }}
      board.appendChild(row);
    }}
  }}

  function handleKey(k) {{
    if (gameOver) return;
    if (k === 'ENTER') {{
      if (currentGuess.length === 5) {{
        guesses.push(currentGuess);
        if (currentGuess === target) {{
          gameOver = true;
          showBanner('🎉 Splendid! You solved it!', '#10B981');
        }} else if (guesses.length === 6) {{
          gameOver = true;
          showBanner('Word was: ' + target, '#EF4444');
        }}
        currentGuess = "";
        renderBoard();
        renderKeyboard();
      }}
    }} else if (k === 'DEL' || k === 'BACKSPACE') {{
      currentGuess = currentGuess.slice(0, -1);
      renderBoard();
    }} else if (/^[A-Z]$/.test(k)) {{
      if (currentGuess.length < 5) {{
        currentGuess += k;
        renderBoard();
      }}
    }}
  }}

  function showBanner(msg, bg) {{
    const b = document.getElementById('banner');
    b.innerText = msg;
    b.style.background = bg;
    b.style.display = 'block';
  }}

  function renderKeyboard() {{
    const kb = document.getElementById('keyboard');
    kb.innerHTML = '';
    const layout = [
      ["Q","W","E","R","T","Y","U","I","O","P"],
      ["A","S","D","F","G","H","J","K","L"],
      ["ENTER","Z","X","C","V","B","N","M","DEL"]
    ];
    layout.forEach(row => {{
      let rEl = document.createElement('div');
      rEl.className = 'kb-row';
      row.forEach(k => {{
        let btn = document.createElement('button');
        btn.className = 'key' + (k.length > 1 ? ' wide' : '');
        btn.innerText = k;
        btn.onclick = () => handleKey(k);
        // check statuses
        if (k.length === 1) {{
          let isCorr = guesses.some(g => g.split('').some((ch, i) => ch === k && target[i] === k));
          let isPres = guesses.some(g => g.includes(k) && target.includes(k));
          let isAbs = guesses.some(g => g.includes(k) && !target.includes(k));
          if (isCorr) btn.classList.add('correct');
          else if (isPres) btn.classList.add('present');
          else if (isAbs) btn.classList.add('absent');
        }}
        rEl.appendChild(btn);
      }});
      kb.appendChild(rEl);
    }});
  }}

  window.addEventListener('keydown', e => {{
    if (e.key === 'Enter') handleKey('ENTER');
    else if (e.key === 'Backspace') handleKey('DEL');
    else if (/^[a-zA-Z]$/.test(e.key)) handleKey(e.key.toUpperCase());
  }});

  newGame();
</script>
</body>
</html>"""


def get_minesweeper_html(theme_primary: str = "#6366F1", theme_bg: str = "#0F172A") -> str:
    """Return self-contained HTML5 Minesweeper game."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Minesweeper Retro</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
  body {{
    background: {theme_bg};
    color: #F8FAFC;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 10px;
  }}
  .card {{
    background: rgba(30, 41, 59, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .top-bar {{
    width: 100%;
    background: #020617;
    border: 2px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }}
  .lcd {{
    font-family: monospace;
    font-size: 1.5rem;
    font-weight: 900;
    color: #EF4444;
    background: #1E1B4B;
    padding: 2px 8px;
    border-radius: 4px;
  }}
  .face-btn {{
    font-size: 1.6rem;
    background: none;
    border: none;
    cursor: pointer;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(9, 36px);
    grid-template-rows: repeat(9, 36px);
    gap: 3px;
    background: #0F172A;
    padding: 8px;
    border-radius: 8px;
  }}
  .cell {{
    background: #334155;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    font-weight: 800;
    cursor: pointer;
  }}
  .cell:hover {{ background: #475569; }}
  .cell.revealed {{ background: #1E293B; cursor: default; }}
  .cell.mine {{ background: #DC2626 !important; }}
  .c-1 {{ color: #38BDF8; }}
  .c-2 {{ color: #4ADE80; }}
  .c-3 {{ color: #F87171; }}
  .c-4 {{ color: #A78BFA; }}
  .c-5 {{ color: #FB923C; }}
  .mode-toggle {{
    margin-top: 12px;
    display: flex;
    gap: 10px;
  }}
  .btn-mode {{
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.85rem;
    font-weight: 700;
    cursor: pointer;
  }}
  .btn-mode.active {{ background: #38BDF8; }}
</style>
</head>
<body>
<div class="card">
  <div class="top-bar">
    <div class="lcd" id="minesLeft">010</div>
    <button class="face-btn" id="face" onclick="initGame()">😊</button>
    <div class="lcd" id="timer">000</div>
  </div>

  <div class="grid" id="grid"></div>

  <div class="mode-toggle">
    <button class="btn-mode active" id="btnDig" onclick="setMode('dig')">⛏️ Dig Mode</button>
    <button class="btn-mode" id="btnFlag" onclick="setMode('flag')">🚩 Flag Mode</button>
  </div>
</div>

<script>
  const ROWS = 9, COLS = 9, MINES = 10;
  let board = [], flags = 0, revealedCount = 0, firstClick = true, isGameOver = false;
  let touchMode = 'dig';
  let timerInterval = null, seconds = 0;

  function setMode(m) {{
    touchMode = m;
    document.getElementById('btnDig').classList.toggle('active', m === 'dig');
    document.getElementById('btnFlag').classList.toggle('active', m === 'flag');
  }}

  function initGame() {{
    board = [];
    flags = 0;
    revealedCount = 0;
    firstClick = true;
    isGameOver = false;
    clearInterval(timerInterval);
    seconds = 0;
    document.getElementById('timer').innerText = '000';
    document.getElementById('face').innerText = '😊';
    document.getElementById('minesLeft').innerText = '010';

    for (let r = 0; r < ROWS; r++) {{
      let row = [];
      for (let c = 0; c < COLS; c++) {{
        row.push({{ mine: false, revealed: false, flagged: false, count: 0 }});
      }}
      board.push(row);
    }}
    render();
  }}

  function placeMines(exR, exC) {{
    let placed = 0;
    while (placed < MINES) {{
      let r = Math.floor(Math.random() * ROWS);
      let c = Math.floor(Math.random() * COLS);
      if ((r === exR && c === exC) || board[r][c].mine) continue;
      board[r][c].mine = true;
      placed++;
    }}
    for (let r = 0; r < ROWS; r++) {{
      for (let c = 0; c < COLS; c++) {{
        if (!board[r][c].mine) {{
          let cnt = 0;
          for (let dr = -1; dr <= 1; dr++) {{
            for (let dc = -1; dc <= 1; dc++) {{
              let nr = r + dr, nc = c + dc;
              if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS && board[nr][nc].mine) cnt++;
            }}
          }}
          board[r][c].count = cnt;
        }}
      }}
    }}
  }}

  function render() {{
    const grid = document.getElementById('grid');
    grid.innerHTML = '';
    for (let r = 0; r < ROWS; r++) {{
      for (let c = 0; c < COLS; c++) {{
        let cell = board[r][c];
        let el = document.createElement('div');
        el.className = 'cell';
        if (cell.revealed) {{
          el.classList.add('revealed');
          if (cell.mine) {{
            el.innerText = '💣';
            el.classList.add('mine');
          }} else if (cell.count > 0) {{
            el.innerText = cell.count;
            el.classList.add('c-' + cell.count);
          }}
        }} else if (cell.flagged) {{
          el.innerText = '🚩';
        }}
        el.onclick = () => {{
          if (touchMode === 'flag') toggleFlag(r, c);
          else reveal(r, c);
        }};
        el.oncontextmenu = (e) => {{
          e.preventDefault();
          toggleFlag(r, c);
        }};
        grid.appendChild(el);
      }}
    }}
  }}

  function toggleFlag(r, c) {{
    if (isGameOver || board[r][c].revealed) return;
    board[r][c].flagged = !board[r][c].flagged;
    flags += board[r][c].flagged ? 1 : -1;
    let rem = Math.max(0, MINES - flags);
    document.getElementById('minesLeft').innerText = rem.toString().padStart(3, '0');
    render();
  }}

  function reveal(r, c) {{
    if (isGameOver || board[r][c].revealed || board[r][c].flagged) return;
    if (firstClick) {{
      firstClick = false;
      placeMines(r, c);
      timerInterval = setInterval(() => {{
        seconds++;
        document.getElementById('timer').innerText = Math.min(999, seconds).toString().padStart(3, '0');
      }}, 1000);
    }}

    let cell = board[r][c];
    cell.revealed = true;
    revealedCount++;

    if (cell.mine) {{
      isGameOver = true;
      clearInterval(timerInterval);
      document.getElementById('face').innerText = '😵';
      // reveal all mines
      for (let ro = 0; ro < ROWS; ro++) {{
        for (let co = 0; co < COLS; co++) {{
          if (board[ro][co].mine) board[ro][co].revealed = true;
        }}
      }}
      render();
      return;
    }}

    if (cell.count === 0) {{
      for (let dr = -1; dr <= 1; dr++) {{
        for (let dc = -1; dc <= 1; dc++) {{
          let nr = r + dr, nc = c + dc;
          if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS && !board[nr][nc].revealed) {{
            reveal(nr, nc);
          }}
        }}
      }}
    }}

    if (revealedCount === ROWS * COLS - MINES) {{
      isGameOver = true;
      clearInterval(timerInterval);
      document.getElementById('face').innerText = '😎';
    }}
    render();
  }}

  initGame();
</script>
</body>
</html>"""


def get_tetris_html(theme_primary: str = "#6366F1", theme_bg: str = "#0F172A") -> str:
    """Return self-contained HTML5 Block Drop (Tetris) game."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Block Drop</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
  body {{
    background: {theme_bg};
    color: #F8FAFC;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 10px;
  }}
  .card {{
    background: rgba(30, 41, 59, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    display: flex;
    gap: 16px;
  }}
  canvas {{
    background: #020617;
    border: 2px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    display: block;
  }}
  .side-panel {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-width: 110px;
  }}
  .stat-card {{
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 6px 12px;
    text-align: center;
    margin-bottom: 8px;
  }}
  .stat-label {{
    font-size: 0.7rem;
    text-transform: uppercase;
    color: #94A3B8;
    font-weight: 700;
  }}
  .stat-val {{
    font-size: 1.2rem;
    font-weight: 800;
    color: #38BDF8;
  }}
  .btn {{
    background: {theme_primary};
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px;
    font-weight: 700;
    cursor: pointer;
  }}
  .touch-controls {{
    display: grid;
    grid-template-columns: repeat(3, 44px);
    grid-template-rows: repeat(2, 40px);
    gap: 4px;
    margin-top: 10px;
  }}
  .tbtn {{
    background: rgba(51, 65, 85, 0.6);
    color: #fff;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
  }}
</style>
</head>
<body>
<div class="card">
  <canvas id="tetris" width="200" height="400"></canvas>
  <div class="side-panel">
    <div>
      <div class="stat-card">
        <div class="stat-label">Score</div>
        <div class="stat-val" id="score">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Lines</div>
        <div class="stat-val" id="lines">0</div>
      </div>
    </div>

    <div>
      <div class="touch-controls">
        <button class="tbtn" style="grid-column:2" onclick="playerRotate()">🔄</button>
        <button class="tbtn" style="grid-column:1;grid-row:2" onclick="playerMove(-1)">⬅️</button>
        <button class="tbtn" style="grid-column:2;grid-row:2" onclick="playerDrop()">⬇️</button>
        <button class="tbtn" style="grid-column:3;grid-row:2" onclick="playerMove(1)">➡️</button>
      </div>
      <button class="btn" onclick="resetGame()" style="width:100%;margin-top:8px;">New Game</button>
    </div>
  </div>
</div>

<script>
  const canvas = document.getElementById('tetris');
  const context = canvas.getContext('2d');
  context.scale(20, 20);

  const colors = [
    null,
    '#EF4444', // T
    '#F59E0B', // O
    '#10B981', // L
    '#3B82F6', // J
    '#8B5CF6', // I
    '#EC4899', // S
    '#06B6D4'  // Z
  ];

  function arenaSweep() {{
    let rowCount = 1;
    outer: for (let y = arena.length - 1; y > 0; --y) {{
      for (let x = 0; x < arena[y].length; ++x) {{
        if (arena[y][x] === 0) continue outer;
      }}
      const row = arena.splice(y, 1)[0].fill(0);
      arena.unshift(row);
      ++y;
      player.score += rowCount * 100;
      player.lines += 1;
      rowCount *= 2;
    }}
  }}

  function collide(arena, player) {{
    const [m, o] = [player.matrix, player.pos];
    for (let y = 0; y < m.length; ++y) {{
      for (let x = 0; x < m[y].length; ++x) {{
        if (m[y][x] !== 0 && (arena[y + o.y] && arena[y + o.y][x + o.x]) !== 0) return true;
      }}
    }}
    return false;
  }}

  function createMatrix(w, h) {{
    const matrix = [];
    while (h--) matrix.push(new Array(w).fill(0));
    return matrix;
  }}

  function createPiece(type) {{
    if (type === 'T') return [[0,0,0],[1,1,1],[0,1,0]];
    if (type === 'O') return [[2,2],[2,2]];
    if (type === 'L') return [[0,3,0],[0,3,0],[0,3,3]];
    if (type === 'J') return [[0,4,0],[0,4,0],[4,4,0]];
    if (type === 'I') return [[0,5,0,0],[0,5,0,0],[0,5,0,0],[0,5,0,0]];
    if (type === 'S') return [[0,6,6],[6,6,0],[0,0,0]];
    if (type === 'Z') return [[7,7,0],[0,7,7],[0,0,0]];
  }}

  function draw() {{
    context.fillStyle = '#020617';
    context.fillRect(0, 0, canvas.width, canvas.height);
    drawMatrix(arena, {{x: 0, y: 0}});
    drawMatrix(player.matrix, player.pos);
  }}

  function drawMatrix(matrix, offset) {{
    matrix.forEach((row, y) => {{
      row.forEach((value, x) => {{
        if (value !== 0) {{
          context.fillStyle = colors[value];
          context.fillRect(x + offset.x, y + offset.y, 1, 1);
          context.strokeStyle = '#0F172A';
          context.lineWidth = 0.05;
          context.strokeRect(x + offset.x, y + offset.y, 1, 1);
        }}
      }});
    }});
  }}

  function merge(arena, player) {{
    player.matrix.forEach((row, y) => {{
      row.forEach((value, x) => {{
        if (value !== 0) arena[y + player.pos.y][x + player.pos.x] = value;
      }});
    }});
  }}

  function rotate(matrix, dir) {{
    for (let y = 0; y < matrix.length; ++y) {{
      for (let x = 0; x < y; ++x) {{
        [matrix[x][y], matrix[y][x]] = [matrix[y][x], matrix[x][y]];
      }}
    }}
    if (dir > 0) matrix.forEach(row => row.reverse());
    else matrix.reverse();
  }}

  function playerDrop() {{
    player.pos.y++;
    if (collide(arena, player)) {{
      player.pos.y--;
      merge(arena, player);
      playerReset();
      arenaSweep();
      updateScore();
    }}
    dropCounter = 0;
  }}

  function playerMove(dir) {{
    player.pos.x += dir;
    if (collide(arena, player)) player.pos.x -= dir;
  }}

  function playerReset() {{
    const pieces = 'TJLOSZI';
    player.matrix = createPiece(pieces[pieces.length * Math.random() | 0]);
    player.pos.y = 0;
    player.pos.x = (arena[0].length / 2 | 0) - (player.matrix[0].length / 2 | 0);
    if (collide(arena, player)) {{
      arena.forEach(row => row.fill(0));
      player.score = 0;
      player.lines = 0;
      updateScore();
    }}
  }}

  function playerRotate() {{
    const pos = player.pos.x;
    let offset = 1;
    rotate(player.matrix, 1);
    while (collide(arena, player)) {{
      player.pos.x += offset;
      offset = -(offset + (offset > 0 ? 1 : -1));
      if (offset > player.matrix[0].length) {{
        rotate(player.matrix, -1);
        player.pos.x = pos;
        return;
      }}
    }}
  }}

  let dropCounter = 0;
  let dropInterval = 800;
  let lastTime = 0;

  function update(time = 0) {{
    const deltaTime = time - lastTime;
    lastTime = time;
    dropCounter += deltaTime;
    if (dropCounter > dropInterval) playerDrop();
    draw();
    requestAnimationFrame(update);
  }}

  function updateScore() {{
    document.getElementById('score').innerText = player.score;
    document.getElementById('lines').innerText = player.lines;
  }}

  function resetGame() {{
    arena.forEach(row => row.fill(0));
    player.score = 0;
    player.lines = 0;
    playerReset();
    updateScore();
  }}

  const arena = createMatrix(10, 20);
  const player = {{ pos: {{x: 0, y: 0}}, matrix: null, score: 0, lines: 0 }};

  window.addEventListener('keydown', e => {{
    if (e.code === 'ArrowLeft') playerMove(-1);
    else if (e.code === 'ArrowRight') playerMove(1);
    else if (e.code === 'ArrowDown') playerDrop();
    else if (e.code === 'ArrowUp') playerRotate();
  }});

  playerReset();
  updateScore();
  update();
</script>
</body>
</html>"""
