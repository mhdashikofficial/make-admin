from flask import Flask, render_template, request
import requests
import json

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    message_type = None

    if request.method == 'POST':
        bot_token = request.form.get('token', '').strip()
        chat_id = request.form.get('chat_id', '').strip()
        text = request.form.get('message', '').strip()
        photo = request.files.get('photo')
        buttons_raw = request.form.get('buttons')

        if not bot_token or not chat_id or not text:
            message = "Bot token, chat ID, and message are required."
            message_type = 'danger'
        else:
            try:
                reply_markup = None

                if buttons_raw:
                    buttons = json.loads(buttons_raw)

                    keyboard = []
                    for btn in buttons:
                        if btn.get('text') and btn.get('url'):
                            keyboard.append([{
                                "text": btn['text'],
                                "url": btn['url']
                            }])

                    if keyboard:
                        reply_markup = {"inline_keyboard": keyboard}

                # ---------------- PHOTO POST ----------------
                if photo and photo.filename:
                    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

                    data = {
                        "chat_id": chat_id,
                        "caption": text,
                        "parse_mode": "HTML"
                    }

                    if reply_markup:
                        data["reply_markup"] = json.dumps(reply_markup)

                    files = {
                        "photo": (photo.filename, photo.stream, photo.mimetype)
                    }

                    r = requests.post(url, data=data, files=files, timeout=30)

                # ---------------- TEXT POST ----------------
                else:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

                    payload = {
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML"
                    }

                    if reply_markup:
                        payload["reply_markup"] = reply_markup

                    r = requests.post(url, json=payload, timeout=20)

                res = r.json()

                if res.get("ok"):
                    message = "✅ Post sent successfully!"
                    message_type = 'success'
                else:
                    message = f"❌ Telegram error: {res.get('description', 'Unknown error')}"
                    message_type = 'danger'

            except Exception as e:
                message = f"Unexpected error: {str(e)}"
                message_type = 'danger'

    return render_template('index.html',
        message=message,
        message_type=message_type
    )

if __name__ == '__main__':
    app.run(debug=True)
