<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Telegram Video Streamer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; }
        .card { max-width: 560px; margin: auto; border-radius: 18px; box-shadow: 0 15px 40px rgba(0,0,0,.25); }
        .telegram-btn { display: inline-flex; align-items: center; padding: 10px 18px; border-radius: 30px; background: linear-gradient(135deg, #0088cc, #229ed9); color: #fff; font-weight: 600; text-decoration: none; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0,136,204,.6); } 70% { box-shadow: 0 0 0 14px rgba(0,136,204,0); } 100% { box-shadow: 0 0 0 0 rgba(0,136,204,0); } }
        .video-player { width: 100%; height: 315px; border: none; border-radius: 12px; }
        .progress { height: 20px; margin: 10px 0; }
    </style>
</head>
<body class="d-flex align-items-center py-4">
<div class="container">
<div class="card p-4">
<h3 class="text-center mb-3">🎥 Telegram Video Stream</h3>
{% if message %}
<div class="alert alert-{{ message_type }}">{{ message }}</div>
{% endif %}
{% if progress %}
<div class="alert alert-info">
    <strong>Status:</strong> {{ progress }}<br>
    <small>Large files take 5-15 min. Refresh page to check.</small>
    <div class="progress">
        <div class="progress-bar" style="width: {{ progress_percent }}%"></div>
    </div>
</div>
{% endif %}
{% if api_error %}
<div class="alert alert-warning">
    <strong>Debug:</strong> {{ api_error }}<br><small>Check logs for details.</small>
</div>
{% endif %}
<form method="POST">
    <h6>Pyrogram Credentials (Required for Large Files)</h6>
    <input class="form-control mb-3" name="api_id" placeholder="API ID (int)" type="number" required>
    <input class="form-control mb-3" name="api_hash" placeholder="API Hash" required>
    <input class="form-control mb-3" name="session_string" placeholder="Session String (1:BQA...)" required>
    <input class="form-control mb-3" name="chat_id" placeholder="@channel or -100xxxx (optional)">
    <div class="input-group mb-3">
        <input class="form-control" name="telegram_link" placeholder="https://t.me/channelname/123" required>
        <button class="btn btn-primary" type="submit">▶️ Start Stream</button>
    </div>
</form>
{% if hls_url %}
<div class="mt-4">
    <h6 class="text-center mb-3">Now Playing:</h6>
    <video id="video" class="video-player" controls autoplay muted></video>
    <div class="text-center mt-2"><small>Powered by Pyrogram + FFmpeg</small></div>
</div>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<script>
    var video = document.getElementById('video');
    var hls_url = "{{ hls_url }}";
    if (Hls.isSupported()) {
        var hls = new Hls();
        hls.loadSource(hls_url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = hls_url;
        video.addEventListener('loadedmetadata', () => video.play());
    }
</script>
{% endif %}
<div class="mt-4 text-center">
    <div class="text-muted small">© 2026 | Large files auto-download to /tmp then HLS</div>
    <a href="https://t.me/alexanderthegreatxx" target="_blank" class="telegram-btn mt-2">Connect on Telegram</a>
</div>
</div>
</div>
</body>
</html>
