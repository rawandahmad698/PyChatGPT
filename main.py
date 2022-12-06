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

import traceback
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
colorama.init(autoreset=True)

# Check if config.json exists
if not os.path.exists("config.json"):
    print(">> config.json is missing. Please create it.")
    print(f"{Fore.RED}>> Exiting...")
    exit(1)

# Read config.json
with open("config.json", "r") as f:
    config = json.load(f)
    # Check if email & password are in config.json
    if "email" not in config or "password" not in config:
        print(">> config.json is missing email or password. Please add them.")
        print(f"{Fore.RED}>> Exiting...")
        exit(1)

    # Get email & password
    email = config["email"]
    password = config["password"]

expired_creds = Auth.expired_creds()
print(f"{Fore.GREEN}>> Checking if credentials are expired...")
if expired_creds:
    print(f"{Fore.RED}>> Your credentials are expired." + f" {Fore.GREEN}Attempting to refresh them...")
    open_ai_auth = Auth.OpenAIAuth(email_address=email, password=password)
    print(f"{Fore.GREEN}>> Credentials have been refreshed.")
    open_ai_auth.begin()
    time.sleep(3)
    is_still_expired = Auth.expired_creds()
    if is_still_expired:
        print(f"{Fore.RED}>> Failed to refresh credentials. Please try again.")
        exit(1)
    else:
        print(f"{Fore.GREEN}>> Successfully refreshed credentials.")
else:
    print(f"{Fore.GREEN}>> Your credentials are valid.")
print(f"{Fore.GREEN}>> Starting chat..." + Fore.RESET)
previous_convo_id = None
access_token = Auth.get_access_token()
    

        
def is_allowed(update: Update) -> bool:
    """Check if the user is sane."""
    if update.effective_user.username not in ['cczhong']:
        update.message.reply_text(
            "You are not allowed to use this bot. Contact @Klingefjord to get access."
        )
        return False
    return True


def reply(update: Update, context: CallbackContext) -> None:
    """Call the OpenAI API."""
    global access_token
    global previous_convo_id
    if not is_allowed(update):
        return
    try:
        if access_token == "":
            print(f"{Fore.RED}>> Access token is missing in /Classes/auth.json.")
        user_input = update.message.text
        answer, previous_convo = Chat.ask(auth_token=access_token,
                                          prompt=user_input,
                                          previous_convo_id=previous_convo_id)
        if answer == "400" or answer == "401":
            print(f"{Fore.RED}>> Your token is invalid. Attempting to refresh..")
            open_ai_auth = Auth.OpenAIAuth(email_address=email, password=password)
            open_ai_auth.begin()
            time.sleep(3)
            access_token = Auth.get_access_token()
            update.message.reply_text("Your token has been refreshed. Please try again.")
        else:
            if previous_convo is not None:
                previous_convo_id = previous_convo
            update.message.reply_text(answer)
    except KeyboardInterrupt:
        print(f"{Fore.RED}>> Exiting...")



def main() -> None:
    """Start the bot."""
   
    updater = Updater("5720915360:AAHL58iLqpPhPRXJyt9srh20a5axfqZdG2o")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram


    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, reply))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()






