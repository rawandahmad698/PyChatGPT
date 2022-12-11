import os
import json

# Get path using os, it's in ./classes/auth.json
path = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(path, "auth.json")
with open(path, "r") as f:
    content = f.read()
    account_dict = {} if content == '' else json.loads(content)
    print(account_dict)
    # account_dict[email] = {"access_token": access_token, "expires_at": expiry}
    # f.write(json.dumps(account_dict))