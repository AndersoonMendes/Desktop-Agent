import json
import queue
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Self
from urllib.parse import parse_qs, urlsplit


def render_playlist_page(items: list[dict], token: str) -> str:
    """Build a local page that plays approved IDs with YouTube's IFrame API."""
    serialized_items = json.dumps(items, ensure_ascii=False)
    serialized_items = (
        serialized_items.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    serialized_token = json.dumps(token)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fila de músicas</title>
  <style>
    body {{ margin: 0; padding: 24px; color: #f5f5f5; background: #111; font: 16px system-ui, sans-serif; }}
    main {{ max-width: 1050px; margin: auto; }}
    #player {{ width: min(100%, 960px); aspect-ratio: 16 / 9; margin: 20px 0; }}
    #player iframe {{ width: 100%; height: 100%; }}
    button {{ padding: 12px 18px; font: inherit; cursor: pointer; }}
    a {{ color: #7dd3fc; }}
    li {{ padding: 5px 0; }}
    .current {{ color: #7dd3fc; font-weight: 700; }}
    #status {{ min-height: 1.5em; }}
  </style>
</head>
<body>
<main>
  <h1>Fila de músicas</h1>
  <p id="status">Carregando o player oficial do YouTube…</p>
  <button id="start" disabled>Iniciar reprodução</button>
  <button id="stop" disabled>Parar fila</button>
  <div id="player"></div>
  <h2>Ordem aprovada</h2>
  <ol id="tracks"></ol>
</main>
<script>
const TRACKS = {serialized_items};
const TOKEN = {serialized_token};
const statusElement = document.getElementById('status');
const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');
const listElement = document.getElementById('tracks');
let player = null;
let playerReady = false;
let currentIndex = 0;
let stopped = false;

for (const track of TRACKS) {{
  const item = document.createElement('li');
  item.dataset.index = String(track.index);
  const link = document.createElement('a');
  link.href = track.url;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.textContent = `${{track.track_title}} — ${{track.video_title}} (${{track.channel}})`;
  item.appendChild(link);
  listElement.appendChild(item);
}}

function report(event) {{
  fetch(`/event?token=${{encodeURIComponent(TOKEN)}}`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(event),
    keepalive: true
  }}).catch(() => {{}});
}}

function setCurrent(index) {{
  if (index < 0 || index >= TRACKS.length) return;
  currentIndex = index;
  for (const item of listElement.children) {{
    item.classList.toggle('current', Number(item.dataset.index) === index);
  }}
}}

function currentVideoId(target) {{
  try {{ return new URL(target.getVideoUrl()).searchParams.get('v'); }}
  catch {{ return null; }}
}}

function onYouTubeIframeAPIReady() {{
  player = new YT.Player('player', {{
    width: '960',
    height: '540',
    playerVars: {{ playsinline: 1, origin: location.origin, enablejsapi: 1 }},
    events: {{
      onReady: () => {{
        playerReady = true;
        player.setShuffle(false);
        player.setLoop(false);
        startButton.disabled = false;
        statusElement.textContent = 'Clique uma vez em “Iniciar reprodução”. Depois, a fila avança sozinha.';
        report({{ type: 'ready' }});
      }},
      onStateChange: onPlayerStateChange,
      onError: onPlayerError,
      onAutoplayBlocked: () => {{
        startButton.disabled = false;
        statusElement.textContent = 'O navegador bloqueou o início automático. Clique em “Iniciar reprodução”.';
      }}
    }}
  }});
}}

function onPlayerStateChange(event) {{
  const videoId = currentVideoId(event.target);
  const idIndex = TRACKS.findIndex(track => track.video_id === videoId);
  const index = idIndex >= 0 ? idIndex : event.target.getPlaylistIndex();
  if (index >= 0) setCurrent(index);
  const track = TRACKS[currentIndex];
  if (event.data === YT.PlayerState.PLAYING) {{
    startButton.disabled = true;
    stopButton.disabled = false;
    statusElement.textContent = `Tocando ${{currentIndex + 1}}/${{TRACKS.length}}: ${{track.track_title}}`;
    report({{ type: 'playing', index: currentIndex, video_id: videoId }});
  }} else if (event.data === YT.PlayerState.PAUSED) {{
    statusElement.textContent = `Pausado: ${{track.track_title}}`;
    report({{ type: 'paused', index: currentIndex, video_id: videoId }});
  }} else if (event.data === YT.PlayerState.ENDED) {{
    statusElement.textContent = `Concluído: ${{track.track_title}}`;
    report({{ type: 'ended', index: currentIndex, video_id: videoId }});
  }}
}}

function onPlayerError(event) {{
  const videoId = currentVideoId(player);
  const idIndex = TRACKS.findIndex(track => track.video_id === videoId);
  const index = idIndex >= 0 ? idIndex : player.getPlaylistIndex();
  if (index >= 0) setCurrent(index);
  const track = TRACKS[currentIndex];
  statusElement.textContent = `Não foi possível tocar “${{track.track_title}}” no player incorporado (erro ${{event.data}}). Pulando para a próxima.`;
  report({{ type: 'error', index: currentIndex, video_id: videoId, code: event.data }});
  if (currentIndex < TRACKS.length - 1 && !stopped) {{
    setTimeout(() => player.nextVideo(), 1500);
  }}
}}

startButton.addEventListener('click', () => {{
  if (!player) return;
  startButton.disabled = true;
  stopButton.disabled = false;
  player.loadPlaylist(TRACKS.map(track => track.video_id), 0, 0);
}});

stopButton.addEventListener('click', () => {{
  stopped = true;
  report({{ type: 'stopped', index: currentIndex }});
  player.stopVideo();
  stopButton.disabled = true;
  statusElement.textContent = 'Fila interrompida.';
}});

window.addEventListener('pagehide', () => report({{ type: 'closed', index: currentIndex }}));
const api = document.createElement('script');
api.src = 'https://www.youtube.com/iframe_api';
api.onerror = () => {{
  statusElement.textContent = 'Não foi possível carregar o player oficial do YouTube.';
  report({{ type: 'fatal', message: 'Falha ao carregar a IFrame Player API.' }});
}};
document.head.appendChild(api);
setTimeout(() => {{
  if (!playerReady) {{
    statusElement.textContent = 'O player do YouTube não respondeu. Verifique a conexão e recarregue a página.';
    report({{ type: 'fatal', message: 'A IFrame Player API não inicializou.' }});
  }}
}}, 30000);
</script>
</body>
</html>"""


class YouTubePlaylistServer:
    """Serve a local player page and receives playback state events."""

    def __init__(self, items: list[dict]) -> None:
        self.events: queue.Queue[dict] = queue.Queue()
        self.token = secrets.token_urlsafe(24)
        self.html = render_playlist_page(items, self.token).encode("utf-8")
        event_queue = self.events
        token = self.token
        page = self.html

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if urlsplit(self.path).path != "/":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(page)

            def do_POST(self) -> None:
                request = urlsplit(self.path)
                received_token = parse_qs(request.query).get("token", [""])[0]
                if request.path != "/event" or received_token != token:
                    self.send_error(403)
                    return
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 4096:
                        raise ValueError("Invalid event size")
                    event = json.loads(self.rfile.read(size))
                    if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                        raise TypeError("Invalid event")
                except (TypeError, ValueError):
                    self.send_error(400)
                    return
                event_queue.put(event)
                self.send_response(204)
                self.end_headers()

            def log_message(self, _format: str, *args: object) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        host, port = self.server.server_address
        self.url = f"http://{host}:{port}/"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
