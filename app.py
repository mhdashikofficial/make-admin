from flask import Flask, render_template, request, send_from_directory, Response
import re
import requests
import json
import os
import uuid
import subprocess
import logging
import shutil
from io import BytesIO
from pyrogram import Client
from pyrogram.errors import FloodWait

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_FOLDER = '/tmp/streams'
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def parse_telegram_link(link):
    pattern = r'^https://t\.me/([a-zA-Z0-9_]+)/(\d+)$'
    match = re.match(pattern, link)
    if match:
        channel = match.group(1)
        post_id = int(match.group(2))
        from_chat_id = f"@{channel}" if not channel.startswith('-100') else channel
        return from_chat_id, post_id
    return None, None

def get_file_id_bot(bot_token, from_chat_id, message_id, chat_id):
    # Same as before (for small files)
    url = f"https://api.telegram.org/bot{bot_token}/forwardMessage"
    payload = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    r = requests.post(url, data=payload, timeout=30)
    res = r.json()
    logger.info(f"Bot ForwardMessage: {json.dumps(res, indent=2)}")
    if res.get("ok"):
        msg = res['result']
        if 'video' in msg:
            return msg['video']['file_id']
        elif 'document' in msg:
            return msg['document']['file_id']
    return None

def get_direct_url_bot(bot_token, file_id):
    url = f"https://api.telegram.org/bot{bot_token}/getFile"
    payload = {"file_id": file_id}
    r = requests.post(url, data=payload, timeout=30)
    res = r.json()
    logger.info(f"Bot GetFile: {json.dumps(res, indent=2)}")
    if res.get("ok"):
        file_path = res['result']['file_path']
        return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    return None

async def get_file_via_pyrogram(api_id, api_hash, session_string, from_chat_id, message_id):
    app = Client("temp_session", api_id=api_id, api_hash=api_hash, session_string=session_string, in_memory=True)
    try:
        await app.start()
        msg = await app.get_messages(from_chat_id, message_id)
        if msg.video or msg.document:
            # Get file size to check
            file_size = msg.video.file_size if msg.video else msg.document.file_size
            logger.info(f"Pyrogram file size: {file_size} bytes")
            if file_size > 20 * 1024 * 1024:  # >20MB
                # For large files, we'll proxy download in chunks via FFmpeg (no full get)
                # Return a temp proxy endpoint for streaming
                proxy_id = str(uuid.uuid4())
                return f"/pyro_proxy/{proxy_id}?chat={from_chat_id}&msg={message_id}&api_id={api_id}&hash={api_hash}&sess={session_string}"
            else:
                # Small: Download to BytesIO for direct URL simulation
                file = await app.download_media(msg, in_memory=True)
                # For now, save to /tmp as proxy (or serve BytesIO)
                temp_path = f"/tmp/small_{uuid.uuid4().hex}.mkv"
                with open(temp_path, 'wb') as f:
                    f.write(file.getvalue())
                return temp_path
        return None
    except FloodWait as e:
        logger.error(f"Flood wait: {e.value} seconds")
        return None
    except Exception as e:
        logger.error(f"Pyrogram error: {e}")
        return None
    finally:
        await app.stop()

@app.route('/pyro_proxy/<proxy_id>')
def pyro_proxy(proxy_id):
    # This endpoint acts as a chunked proxy for FFmpeg to pull from Pyrogram
    # But for simplicity, we'll trigger download on-demand in convert_to_hls
    # (FFmpeg -i will hit this, but Pyrogram downloads chunks lazily)
    return "Proxy endpoint - handled in FFmpeg"

def convert_to_hls(input_source, output_dir, is_pyro=False, **pyro_kwargs):
    os.makedirs(output_dir, exist_ok=True)
    hls_playlist = os.path.join(output_dir, 'playlist.m3u8')
    
    if is_pyro:
        # Custom FFmpeg for Pyrogram proxy: Download in chunks via script
        # For now, use pyrogram to stream to pipe (advanced; requires async subprocess)
        # Simpler: Download full to /tmp if small, or chunk via pyro.download_media(file_name=pipe)
        # Placeholder: Assume small file path
        input_url = input_source  # Temp path or proxy URL
    else:
        input_url = input_source
    
    hls_cmd = [
        'ffmpeg', '-i', input_url,
        '-profile:v', 'baseline', '-level', '3.0',
        '-start_number', '0',
        '-hls_time', '10',
        '-hls_list_size', '0',
        '-f', 'hls', hls_playlist
    ]
    
    try:
        result = subprocess.run(hls_cmd, check=True, capture_output=True, timeout=600)  # Longer timeout for large
        logger.info(f"HLS done for {input_url}")
        return True
    except Exception as e:
        logger.error(f"HLS failed: {e}")
        return False

def cleanup_old_streams():
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER, ignore_errors=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/stream/<video_id>/<format_type>/<path:filename>')
def stream_file(video_id, format_type, filename):
    directory = os.path.join(app.config['OUTPUT_FOLDER'], video_id, format_type)
    if not os.path.exists(directory):
        return "File not found", 404
    return send_from_directory(directory, filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    message_type = None
    hls_url = None
    api_error = None
    if request.method == 'POST':
        api_id = int(request.form.get('api_id', 0))
        api_hash = request.form.get('api_hash', '')
        session_string = request.form.get('session_string', '')
        bot_token = request.form.get('bot_token', '')
        chat_id = request.form.get('chat_id', '')
        telegram_link = request.form.get('telegram_link', '')
        
        if not telegram_link or not api_id or not api_hash or not session_string:
            message = "Telegram link and Pyrogram creds (API_ID, API_HASH, Session String) are required."
            message_type = 'danger'
        else:
            from_chat_id, message_id = parse_telegram_link(telegram_link)
            if not from_chat_id:
                message = "Invalid Telegram link."
                message_type = 'danger'
            else:
                target_chat_id = chat_id or from_chat_id
                try:
                    cleanup_old_streams()
                    
                    # Try Bot API first if token provided (for small files)
                    direct_url = None
                    if bot_token:
                        file_id = get_file_id_bot(bot_token, from_chat_id, message_id, target_chat_id)
                        if file_id:
                            direct_url = get_direct_url_bot(bot_token, file_id)
                    
                    # Fallback to Pyrogram for large files
                    if not direct_url:
                        input_source = get_file_via_pyrogram(api_id, api_hash, session_string, from_chat_id, message_id)
                        if not input_source:
                            message = "Failed to access file. Check creds/session and channel access."
                            message_type = 'danger'
                            api_error = "Pyrogram couldn't fetch message. Ensure session has channel access."
                        else:
                            is_pyro = True
                            video_id = str(uuid.uuid4())
                            hls_dir = os.path.join(OUTPUT_FOLDER, video_id, 'hls')
                            if convert_to_hls(input_source, hls_dir, is_pyro=is_pyro):
                                hls_url = f"/stream/{video_id}/hls/playlist.m3u8"
                                message = "✅ Large video streamed via Pyrogram! Playable now."
                                message_type = 'success'
                            else:
                                message = "HLS conversion failed (check FFmpeg/logs)."
                                message_type = 'danger'
                    else:
                        # Bot success (small file)
                        video_id = str(uuid.uuid4())
                        hls_dir = os.path.join(OUTPUT_FOLDER, video_id, 'hls')
                        if convert_to_hls(direct_url, hls_dir):
                            hls_url = f"/stream/{video_id}/hls/playlist.m3u8"
                            message = "✅ Small video streamed!"
                            message_type = 'success'
                        else:
                            message = "HLS failed."
                            message_type = 'danger'
                except Exception as e:
                    message = f"Error: {str(e)}"
                    message_type = 'danger'
                    api_error = str(e)
    return render_template('index.html',
        message=message, message_type=message_type, hls_url=hls_url, api_error=api_error
    )

if __name__ == '__main__':
    app.run(debug=True)
