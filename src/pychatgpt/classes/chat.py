# Builtins
import json
import os
import re
import uuid
from typing import Tuple

# Requests
import requests

# Colorama
import colorama
colorama.init(autoreset=True)


def ask(
        auth_token: Tuple,
        prompt: str,
        conversation_id:
        str or None,
        previous_convo_id: str or None,
        proxies: str or dict or None
) -> Tuple[str, str or None, str or None]:
    auth_token, expiry = auth_token

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}',
        'Accept': 'text/event-stream',
        'Referer': 'https://chat.openai.com/chat',
        'Origin': 'https://chat.openai.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        'X-OpenAI-Assistant-App-Id': ''
    }

    if previous_convo_id is None:
        previous_convo_id = str(uuid.uuid4())

    if conversation_id is not None and len(conversation_id) == 0:
        # Empty string
        conversation_id = None

    # print("Conversation ID:", conversation_id)
    # print("Previous Conversation ID:", previous_convo_id)

    data = {
        "action": "variant",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": {"content_type": "text", "parts": [str(prompt)]},
            }
        ],
        "conversation_id": conversation_id,
        "parent_message_id": previous_convo_id,
        "model": "text-davinci-002-render"
    }
    try:
        session = requests.Session()
        if proxies is not None:
            if isinstance(proxies, str):
                proxies = {'http': proxies, 'https': proxies}

            # Set the proxies
            session.proxies.update(proxies)

        response = session.post(
            "https://chat.openai.com/backend-api/conversation",
            headers=headers,
            data=json.dumps(data)
        )
        if response.status_code == 200:
            response_text = response.text.replace("data: [DONE]", "")
            data = re.findall(r'data: (.*)', response_text)[-1]
            as_json = json.loads(data)
            return as_json["message"]["content"]["parts"][0], as_json["message"]["id"], as_json["conversation_id"]
        elif response.status_code == 401:
            # Check if auth.json exists, if so, delete it
            if os.path.exists("auth.json"):
                os.remove("auth.json")

            return f"[Status Code] 401 | [Response Text] {response.text}", None, None
        elif response.status_code >= 500:
            print(">> Looks like the server is either overloaded or down. Try again later.")
            return f"[Status Code] {response.status_code} | [Response Text] {response.text}", None, None
        else:
            return f"[Status Code] {response.status_code} | [Response Text] {response.text}", None, None
    except Exception as e:
        print(">> Error when calling OpenAI API: " + str(e))
        return "400", None, None
