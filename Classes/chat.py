# Builtins
import json
import re
import uuid
from typing import Tuple

# Requests
import requests


def ask(auth_token: str, prompt, previous_convo_id: str or None) -> Tuple[str, str or None]:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    if previous_convo_id is None:
        previous_convo_id = str(uuid.uuid4())

    data = {
        "action": "next",
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": {"content_type": "text", "parts": [prompt]}
            }
        ],
        "conversation_id": None,
        "parent_message_id": previous_convo_id,
        "model": "text-davinci-002-render"
    }
    try:
        response = requests.post(
            "https://chat.openai.com/backend-api/conversation",
            headers=headers,
            data=json.dumps(data)
        )
        if response.status_code == 200:
            response_text = response.text.replace("data: [DONE]", "")
            data = re.findall(r'data: (.*)', response_text)[-1]
            as_json = json.loads(data)
            return as_json["message"]["content"]["parts"][0], as_json["conversation_id"]
        elif response.status_code == 401:
            print("Error: " + response.text)
            return "401", None
        else:
            print("Error: " + response.text)
            return "Error", None
    except Exception as e:
        print(">> Error when calling OpenAI API: " + str(e))
        return "400", None


