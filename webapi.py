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

AI_PREV_CONVO = None
app = FastAPI()


@app.get("/")
def read_root():
    return {"Only accept:": "'host:port/{query}'"}


@app.get("/{prompt}")
def chatGPT(prompt: str, previous_convo: str = None) -> str:
    global AI_PREV_CONVO
    print(f"{Fore.GREEN}>> Starting chat..." + Fore.RESET)
    access_token = Auth.get_access_token()
    if access_token == "":
        print(f"{Fore.RED}>> Access token is missing in /Classes/auth.json.")
        pass
    answer, previous_convo = Chat.ask(auth_token=access_token,
                                      prompt=prompt,
                                      previous_convo_id=AI_PREV_CONVO)
    if answer == "400" or answer == "401":
        result = ">> Token invalid, please contact the owner to refresh."
        print(f"{Fore.RED}>> Your token is invalid. Attempting to refresh..")
        pass
    else:
        result = answer
        if previous_convo is not None:
            AI_PREV_CONVO = previous_convo
    print(result)
    return result


if __name__ == "__main__":
    prompt = input("You: ")
    print(chatGPT(prompt))
