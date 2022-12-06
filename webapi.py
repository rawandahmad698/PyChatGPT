#!/usr/bin/env python3

# Builtins
import json
import os
import time

# Local
from Classes import auth as Auth
from Classes import chat as Chat

# Fancy stuff
import colorama
from colorama import Fore
from typing import Union

from fastapi import FastAPI

PREVIOUS_CONVO_ID = None
app = FastAPI()


@app.get("/")
def read_root():
    return {"error": "Missing query. e.g {host:port/{your_query}"}


@app.get("/{prompt}")
def chat_gpt(prompt: str, previous_convo: str = None) -> str:
    global PREVIOUS_CONVO_ID
    print(f"{Fore.GREEN}>> Starting chat..." + Fore.RESET)
    access_token = Auth.get_access_token()
    if access_token == "":
        print(f"{Fore.RED}>> Access token is missing in /Classes/auth.json.")
        raise Exception(
            "error: access token is missing in /Classes/auth.json, your may run main.py or refresh manually."
        )
    answer, previous_convo = Chat.ask(auth_token=access_token,
                                      prompt=prompt,
                                      previous_convo_id=PREVIOUS_CONVO_ID)
    if answer == "400" or answer == "401":
        result = ">> Token invalid, please contact the owner to refresh."
        print(f"{Fore.RED}>> Your token is invalid. Attempting to refresh..")
        raise Exception(
            "error: access token is invalid in /Classes/auth.json, your may run main.py or refresh manually."
        )
    else:
        result = answer
        if previous_convo is not None:
            PREVIOUS_CONVO_ID = previous_convo
    return result


if __name__ == "__main__":
    prompt = input("You: ")
    print(chat_gpt(prompt))
