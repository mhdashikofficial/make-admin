# app.py
from flask import Flask, render_template, request
import requests
import json

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    message_type = None  # 'success', 'error', 'info'
    if request.method == 'POST':
        bot_token = request.form['token']
        channels_text = request.form['channel']
        username = request.form['username'].lstrip('@')

        channel_links = [link.strip() for link in channels_text.split('\n') if link.strip()]

        if not channel_links:
            return render_template('index.html', error="Please provide at least one channel link.")

        api_url = f"https://api.telegram.org/bot{bot_token}/"

        def api_call(method, params=None):
            if params is None:
                params = {}
            r = requests.post(api_url + method, json=params)
            return r.json()

        # First, fetch user ID from recent updates
        updates = api_call('getUpdates', {'limit': 10, 'timeout': 1})['result']
        user_id = None
        for update in reversed(updates):  # Check latest first
            if 'message' in update and 'from' in update['message']:
                user = update['message']['from']
                if user.get('username') == username:
                    user_id = user['id']
                    break

        if not user_id:
            return render_template('index.html', error="Could not find user ID. Please ensure the user has recently interacted with the bot (e.g., sent a /start message).")

        # Now promote in each channel
        results = []
        success_count = 0
        for link in channel_links:
            # Extract channel username
            if 't.me' in link and '/' in link:
                channel_us = '@' + link.split('/')[-1].split('?')[0].split('#')[0].lstrip('@')
            else:
                channel_us = link

            # Get chat info
            chat = api_call('getChat', {'chat_id': channel_us})
            if not chat.get('ok'):
                results.append(f"Failed for {link}: {chat.get('description', 'Unknown error')}")
                continue

            chat_id = chat['result']['id']

            # Promote params (adjust rights as needed)
            promote_params = {
                'chat_id': chat_id,
                'user_id': user_id,
                'can_post_messages': True,
                'can_edit_messages': True,
                'can_delete_messages': True,
                'can_manage_video_chats': True,
                'can_restrict_members': True,
                'can_promote_members': True,  # Full admin rights
                'can_change_info': True,
                'can_invite_users': True,
                'can_pin_messages': True
            }

            res = api_call('promoteChatMember', promote_params)
            if res.get('ok'):
                success_count += 1
                results.append(f"✅ Success for {link}")
            else:
                results.append(f"❌ Failed for {link}: {res.get('description', 'Unknown error')}")

        # Prepare message
        results_str = '\n'.join(results)
        if success_count == len(channel_links):
            message = f"All channels updated successfully!\n{results_str}"
            message_type = 'success'
        else:
            message = f"Completed with {success_count}/{len(channel_links)} successes:\n{results_str}"
            message_type = 'info'

    return render_template('index.html', message=message, message_type=message_type)

if __name__ == '__main__':
    app.run(debug=True)
