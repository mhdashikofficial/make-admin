from flask import Flask, render_template, request
import requests
import json
import re
app = Flask(__name__)
@app.route('/', methods=['GET', 'POST'])
def index():
    message = None
    message_type = None # 'success', 'warning', 'danger'
    token = ''
    channels_text = ''
    username = ''
  
    if request.method == 'POST':
        bot_token = request.form['token'].strip()
        channels_text = request.form['channel'].strip()
        username_input = request.form['username'].strip().lstrip('@')
      
        if username_input:
            username = '@' + username_input # For display
      
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
                    r = requests.post(api_url + method, json=params, timeout=30) # Increased to 30s
                    return r.json() # NEW: Always return JSON for error details
                except requests.exceptions.Timeout:
                    raise Exception("Request timed out. Telegram API may be slow; try again or check your connection.")
                except requests.exceptions.RequestException as e:
                    # Mask token in errors for security
                    error_msg = str(e).replace(bot_token, '***TOKEN***')
                    raise Exception(f"API request failed: {error_msg}")
            try:
                # Validate token first
                me = api_call('getMe')
                if not me.get('ok'):
                    raise Exception(f"Invalid bot token: {me.get('description', 'Unknown error')}")
                # Clear any existing webhook to avoid 409 conflicts and drop pending
                webhook_clear = api_call('deleteWebhook', {'drop_pending_updates': True})
                if not webhook_clear.get('ok'):
                    raise Exception(f"Failed to clear webhook: {webhook_clear.get('description', 'Unknown error')}")
                # Double-fetch strategy for reliability
                # First: Short poll to acknowledge any immediate pending (post-drop)
                _ = api_call('getUpdates', {'limit': 1, 'timeout': 1})
              
                # Second: Long poll for fresh messages (e.g., the one just sent)
                updates = api_call('getUpdates', {'limit': 200, 'timeout': 20})['result']
              
                # ENHANCED Debug - collect usernames and details
                found_usernames = set()
                update_details = []
                for i, update in enumerate(updates):
                    detail = f"Update {i+1}: "
                    if 'message' in update:
                        msg = update['message']
                        from_user = msg.get('from', {})
                        username = from_user.get('username')
                        if username:
                            found_usernames.add('@' + username)
                            detail += f"From @{username} (ID: {from_user.get('id')})"
                        else:
                            first = from_user.get('first_name', 'Unknown')
                            last = from_user.get('last_name', '')
                            detail += f"From anonymous user '{first} {last}' (ID: {from_user.get('id')})"
                        text = msg.get('text', 'No text (possibly media/sticker)')
                        detail += f" | Text: '{text[:50]}...'"
                    elif 'callback_query' in update:
                        detail += "Callback query (button press)"
                    else:
                        detail += f"Other type: {list(update.keys())}"
                    update_details.append(detail)
              
                user_id = None
                for update in reversed(updates): # Check latest first
                    if 'message' in update and 'from' in update['message']:
                        user = update['message']['from']
                        if user.get('username', '').lower() == username_input.lower():
                            user_id = user['id']
                            break
                if not user_id:
                    debug_info = f"\n\nDebug: Found {len(updates)} recent updates:\n" + '\n'.join(update_details)
                    if not updates:
                        message = f"No recent updates found for @{username_input}. Ensure you sent a message *after* the previous submit (or start fresh).{debug_info}"
                    else:
                        message = f"@{username_input} not in recent updates (checked latest first).{debug_info}\n\nTroubleshoot: 1) Send '/start hello' (include text) right now. 2) Wait 5s, resubmit. 3) If anonymous in debug, set a username in Telegram settings."
                    message_type = 'danger'
                else:
                    # Promotion code
                    results = []
                    success_count = 0
                    total = len(channel_links)
                    for link in channel_links:
                        try:
                            # Extraction (unchanged)
                            extracted = link.split('/')[-1].split('?')[0].split('#')[0].lstrip('@')
                            if extracted.startswith('+'):
                                raise Exception("Private invite links (starting with +) are not supported. Please use the channel's public @username instead (found in channel settings or info). If private without @username, provide the numeric chat ID (e.g., -1001234567890).")
                            if not extracted:
                                raise Exception("Invalid link format. Expected t.me/username, @username, or numeric ID like -1001234567890.")
                           
                            if re.match(r'^-?\d+$', extracted):
                                chat_id_input = extracted
                            else:
                                chat_id_input = '@' + extracted
                           
                            # Get chat info
                            chat = api_call('getChat', {'chat_id': chat_id_input})
                            if not chat.get('ok'):
                                raise Exception(chat.get('description', 'Invalid channel or bot not in channel'))
                            chat_data = chat['result']
                            chat_id = chat_data['id']
                            chat_type = chat_data['type']
                            has_linked = chat_data.get('linked_chat_id') is not None # NEW: For DMs in channels
                           
                            # NEW: Pre-check user status with getChatMember
                            member = api_call('getChatMember', {'chat_id': chat_id, 'user_id': user_id})
                            if not member.get('ok'):
                                raise Exception(f"Failed to get member status: {member.get('description', 'Unknown error')}")
                            member_status = member['result']['status']
                            if member_status == 'administrator':
                                raise Exception("User is already an administrator—no changes made.")
                            elif member_status not in ['member', 'subscriber', 'creator']:
                                raise Exception(f"User status '{member_status}'—must be a member/subscriber to promote.")
                            
                            # UPDATED: Minimal & type-safe permissions
                            promote_params = {
                                'chat_id': chat_id,
                                'user_id': user_id,
                                'is_anonymous': False,
                            }
                            if chat_type == 'channel':
                                # Minimal for channels: Focus on posting/editing
                                promote_params.update({
                                    'can_post_messages': True,
                                    'can_edit_messages': True,
                                    'can_delete_messages': True,
                                    'can_manage_chat': True,  # Includes promote rights
                                })
                                if has_linked:
                                    promote_params['can_manage_direct_messages'] = True
                            else:  # Supergroup/group: Add group-specific minimally
                                promote_params.update({
                                    'can_change_info': True,
                                    'can_delete_messages': True,
                                    'can_invite_users': True,
                                    'can_restrict_members': True,
                                    'can_promote_members': True,
                                    'can_pin_messages': True,
                                    'can_manage_video_chats': True,
                                })
                                # Stories optional—add only if needed
                                promote_params['can_post_stories'] = True
                            
                            res = api_call('promoteChatMember', promote_params)
                            if not res.get('ok'):
                                desc = res.get('description', 'Unknown promotion error')
                                if 'already administrator' in desc.lower() or 'chat_admin_required' in desc.lower():
                                    raise Exception(f"Admin-related issue: {desc} (Check bot has 'Add Administrators' permission).")
                                elif 'user not participant' in desc.lower():
                                    raise Exception("User must be a member of the channel first.")
                                elif 'right_forbidden' in desc.lower() or 'not enough rights' in desc.lower():
                                    raise Exception(f"Bot lacks promotion rights: {desc}. Fix: In channel settings > Administrators > Your Bot > Enable 'Add new administrators'.")
                                elif 'invalid parameter' in desc.lower():
                                    raise Exception(f"Permissions mismatch for chat type. Details: {desc}")
                                else:
                                    raise Exception(f"Promotion failed: {desc}")
                            success_count += 1
                            results.append(f"✅ Success for {link} (type: {chat_type}, DMs: {has_linked}, was: {member_status})")
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
                # Enhanced error message
                error_str = str(e)
                if '401' in error_str:
                    message = "Invalid bot token (401 Unauthorized). Regenerate via @BotFather."
                elif '409' in error_str:
                    message = f"409 Conflict detected (likely webhook or multiple instances). We've attempted to clear the webhook—try again. If it persists, ensure no other apps are using this bot token."
                elif 'timed out' in error_str.lower():
                    message = "Request timed out (network/API delay). We've increased timeouts—try again in a moment or check your internet/VPN."
                elif '400' in error_str and 'getChat' in error_str:
                    message = "400 Bad Request on getChat: Invalid channel format or bot not added to channel. Ensure links use @username (e.g., https://t.me/channelname or @channelname), or numeric ID (e.g., -1001234567890), and bot is admin."
                elif '400' in error_str and 'promoteChatMember' in error_str:
                    message = "400 Bad Request on promoteChatMember: Likely bot permissions (needs 'Add Administrators'), user already admin, or not a member. Exact API error in results above."
                elif '400' in error_str and 'getChatMember' in error_str:
                    message = "400 on getChatMember: User not found in chat—ensure they're a member."
                else:
                    message = f"Unexpected error: {error_str}. Please check your bot token and permissions."
                message_type = 'danger'
        token = bot_token # Repopulate non-sensitive fields; token as password so not repopulated
    return render_template('index.html',
                          message=message,
                          message_type=message_type,
                          token=token,
                          channels_text=channels_text,
                          username=username)
if __name__ == '__main__':
    app.run(debug=True)
