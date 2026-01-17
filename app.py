# app.py
from flask import Flask, render_template, request
import requests
import json

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    message_type = None  # 'success', 'warning', 'danger'
    token = ''
    channels_text = ''
    username = ''
    
    if request.method == 'POST':
        bot_token = request.form['token'].strip()
        channels_text = request.form['channel'].strip()
        username_input = request.form['username'].strip().lstrip('@')
        
        if username_input:
            username = '@' + username_input  # For display
        
        channel_links = [link.strip() for link in channels_text.split('\n') if link.strip()]

        if not bot_token:
            message = "Bot token is required."
            message_type = 'danger'
        elif not channel_links:
            message = "Please provide at least one channel link."
            message_type = 'danger'
        elif not username_input:
            message = "Username is required."
            message_type = 'danger'
        else:
            api_url = f"https://api.telegram.org/bot{bot_token}/"

            def api_call(method, params=None):
                try:
                    if params is None:
                        params = {}
                    r = requests.post(api_url + method, json=params, timeout=10)
                    r.raise_for_status()  # Raises HTTPError for bad responses
                    return r.json()
                except requests.exceptions.RequestException as e:
                    raise Exception(f"API request failed: {str(e)}")

            try:
                # Fetch user ID from recent updates (increase limit for better chance)
                updates = api_call('getUpdates', {'limit': 100, 'timeout': 5})['result']
                user_id = None
                for update in reversed(updates):  # Check latest first
                    if 'message' in update and 'from' in update['message']:
                        user = update['message']['from']
                        if user.get('username', '').lower() == username_input.lower():
                            user_id = user['id']
                            break

                if not user_id:
                    message = f"Could not find user ID for @{username_input}. Please ensure the user has recently interacted with the bot (e.g., sent a /start message to resolve their ID)."
                    message_type = 'danger'
                else:
                    # Now promote in each channel
                    results = []
                    success_count = 0
                    total = len(channel_links)
                    for link in channel_links:
                        try:
                            # Extract channel username
                            if 't.me' in link and '/' in link:
                                channel_us = '@' + link.split('/')[-1].split('?')[0].split('#')[0].lstrip('@')
                            else:
                                channel_us = link.strip()

                            if not channel_us.startswith('@'):
                                channel_us = '@' + channel_us

                            # Get chat info
                            chat = api_call('getChat', {'chat_id': channel_us})
                            if not chat.get('ok'):
                                raise Exception(chat.get('description', 'Invalid channel or bot not in channel'))

                            chat_id = chat['result']['id']

                            # Promote params (full admin rights)
                            promote_params = {
                                'chat_id': chat_id,
                                'user_id': user_id,
                                'is_anonymous': False,
                                'can_manage_chat': True,
                                'can_delete_messages': True,
                                'can_manage_video_chats': True,
                                'can_restrict_members': True,
                                'can_promote_members': True,
                                'can_change_info': True,
                                'can_invite_users': True,
                                'can_post_stories': True,
                                'can_edit_stories': True,
                                'can_delete_stories': True
                            }

                            res = api_call('promoteChatMember', promote_params)
                            if res.get('ok'):
                                success_count += 1
                                results.append(f"✅ Success for {link}")
                            else:
                                raise Exception(res.get('description', 'Unknown promotion error'))
                        except Exception as e:
                            results.append(f"❌ Failed for {link}: {str(e)}")

                    # Prepare message
                    results_str = '\n'.join(results)
                    total_str = f"{success_count}/{total}"
                    if success_count == total:
                        message = f"All channels updated successfully! ({total_str})\n{results_str}"
                        message_type = 'success'
                    elif success_count == 0:
                        message = f"No channels were updated. Check the errors below:\n{results_str}"
                        message_type = 'danger'
                    else:
                        message = f"Partially successful ({total_str}). Details:\n{results_str}"
                        message_type = 'warning'

            except Exception as e:
                message = f"Unexpected error: {str(e)}. Please check your bot token and permissions."
                message_type = 'danger'

        token = bot_token  # Repopulate non-sensitive fields; token as password so not repopulated

    return render_template('index.html', 
                          message=message, 
                          message_type=message_type,
                          token=token, 
                          channels_text=channels_text, 
                          username=username)

if __name__ == '__main__':
    app.run(debug=True)
