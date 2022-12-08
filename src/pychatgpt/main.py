#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Builtins
import time
import os
from queue import Queue

# Local
from .classes import openai as OpenAI
from .classes import chat as ChatHandler
from .classes import spinner as Spinner
from .classes import exceptions as Exceptions

# Fancy stuff
import colorama
from colorama import Fore

colorama.init(autoreset=True)

class Options:
    def __init__(self,
                 proxies: str or dict or None = None,
                 verify: bool = True,
                 track: bool or None = False,
                 chat_log: str or None = None,
                 id_log: str or None = None):

        self.proxies = proxies
        self.track = track
        self.verify = verify
        self.chat_log = chat_log
        self.id_log = id_log
        self._setup()

    def _setup(self):
        # If track is enabled, create the chat log and id log files if they don't exist
        if not isinstance(self.track, bool):
            raise Exceptions.PyChatGPTException("Options to track conversation must be a boolean.")

        if self.track:
            if self.chat_log is not None:
                self._create_if_not_exists(self.chat_log)
            else:
                # Create a chat log file called chat_log.txt
                self.chat_log = "chat_log.txt"
                self._create_if_not_exists(self.chat_log)

            if self.id_log is not None:
                if not os.path.exists(self.id_log):
                    with open(self.id_log, 'w') as f:
                        f.write("")
            else:
                # Create a chat log file called id_log.txt
                self.id_log = "id_log.txt"
                self._create_if_not_exists(self.id_log)

    @staticmethod
    def _create_if_not_exists(file: str):
        if not os.path.exists(file):
            with open(file, 'w') as f:
                f.write("")


class Chat:
    def __init__(self, email, password, options: Options or None = None):
        self.email = email
        self.password = password
        self.options = options

        self.conversation_id: str or None = None
        self.previous_convo_id: int or None = None

        self.__auth_access_token: str or None = None
        self.__auth_access_token_expiry: int or None = None
        self.__chat_history: list or None = None

        self._setup()

    def _setup(self):
        if self.options is not None:
            if self.options.proxies is not None:
                if not isinstance(self.options.proxies, dict):
                    if not isinstance(self.options.proxies, str):
                        raise Exceptions.PyChatGPTException("Proxies must be a string or dictionary.")
                    else:
                        self.proxies = {"http": self.options.proxies, "https": self.options.proxies}

            if self.options.track:
                if not isinstance(self.options.chat_log, str) or not isinstance(self.options.id_log, str):
                    raise Exceptions.PyChatGPTException(
                        "When saving a chat, file paths for chat_log and id_log must be strings.")
                elif len(self.options.chat_log) == 0 or len(self.options.id_log) == 0:
                    raise Exceptions.PyChatGPTException(
                        "When saving a chat, file paths for chat_log and id_log cannot be empty.")

                self.__chat_history = []

        if not self.email or not self.password:
            print(f"{Fore.RED}>> You must provide an email and password when initializing the class.")
            raise Exceptions.PyChatGPTException("You must provide an email and password when initializing the class.")

        if not isinstance(self.email, str) or not isinstance(self.password, str):
            print(f"{Fore.RED}>> Email and password must be strings.")
            raise Exceptions.PyChatGPTException("Email and password must be strings.")

        if len(self.email) == 0 or len(self.password) == 0:
            print(f"{Fore.RED}>> Email cannot be empty.")
            raise Exceptions.PyChatGPTException("Email cannot be empty.")

        if self.options is not None and self.options.track:
            try:
                with open(self.options.id_log, "r") as f:
                    # Check if there's any data in the file
                    if len(f.read()) > 0:
                        self.previous_convo_id = f.readline().strip()
                        self.conversation_id = f.readline().strip()

            except IOError:
                raise Exceptions.PyChatGPTException("When resuming a chat, conversation id and previous conversation id in id_log must be separated by newlines.")
            except Exception:
                raise Exceptions.PyChatGPTException("When resuming a chat, there was an issue reading id_log, make sure that it is formatted correctly.")

        # Check for access_token & access_token_expiry in env
        if OpenAI.token_expired():
            print(f"{Fore.RED}>> Access Token missing or expired."
                  f" {Fore.GREEN}Attempting to create them...")
            self._create_access_token()
        else:
            access_token, expiry = OpenAI.get_access_token()
            self.__auth_access_token = access_token
            self.__auth_access_token_expiry = expiry

            try:
                self.__auth_access_token_expiry = int(self.__auth_access_token_expiry)
            except ValueError:
                print(f"{Fore.RED}>> Expiry is not an integer.")
                raise Exceptions.PyChatGPTException("Expiry is not an integer.")

            if self.__auth_access_token_expiry < time.time():
                print(f"{Fore.RED}>> Your access token is expired. {Fore.GREEN}Attempting to recreate it...")
                self._create_access_token()

    def _create_access_token(self) -> bool:
        openai_auth = OpenAI.Auth(email_address=self.email, password=self.password, proxy=self.options.proxies)
        openai_auth.create_token()

        # If after creating the token, it's still expired, then something went wrong.
        is_still_expired = OpenAI.token_expired()
        if is_still_expired:
            print(f"{Fore.RED}>> Failed to create access token.")
            return False

        # If created, then return True
        return True

    def ask(self, prompt: str, rep_queue: Queue or None = None) -> str or None:
        if prompt is None:
            print(f"{Fore.RED}>> Enter a prompt.")
            raise Exceptions.PyChatGPTException("Enter a prompt.")

        if not isinstance(prompt, str):
            raise Exceptions.PyChatGPTException("Prompt must be a string.")

        if len(prompt) == 0:
            raise Exceptions.PyChatGPTException("Prompt cannot be empty.")

        if rep_queue is not None and not isinstance(rep_queue, Queue):
            raise Exceptions.PyChatGPTException("Cannot enter a non-queue object as the response queue for threads.")

        # Check if the access token is expired
        if OpenAI.token_expired():
            print(f"{Fore.RED}>> Your access token is expired. {Fore.GREEN}Attempting to recreate it...")
            did_create = self._create_access_token()
            if did_create:
                print(f"{Fore.GREEN}>> Successfully recreated access token.")
            else:
                print(f"{Fore.RED}>> Failed to recreate access token.")
                raise Exceptions.PyChatGPTException("Failed to recreate access token.")

        # Get access token
        access_token = OpenAI.get_access_token()


        answer, previous_convo, convo_id = ChatHandler.ask(auth_token=access_token,
                                                           prompt=prompt,
                                                           conversation_id=self.conversation_id,
                                                           previous_convo_id=self.previous_convo_id,
                                                           proxies=self.proxies)

        if rep_queue is not None:
            rep_queue.put((prompt, answer))

        if answer == "400" or answer == "401":
            print(f"{Fore.RED}>> Failed to get a response from the API.")
            return None

        self.conversation_id = convo_id
        self.previous_convo_id = previous_convo

        if self.options.track:
            self.__chat_history.append("You: " + prompt)
            self.__chat_history.append("Chat GPT: " + answer)
            self.save_data()


        return answer

    def save_data(self):
        if self.options.track:
            try:
                with open(self.options.chat_log, "a") as f:
                    f.write("\n".join(self.__chat_history))
                self.__chat_history = []
                with open(self.options.id_log, "w") as f:
                    f.write(str(self.previous_convo_id) + "\n")
                    f.write(str(self.conversation_id) + "\n")
            except Exception as ex:
                print(f"{Fore.RED}>> Failed to save chat and ids to chat log and id_log."
                      f"{ex}")

    def cli_chat(self, rep_queue: Queue or None = None):
        """
        Start a CLI chat session.
        :param rep_queue:  A queue to put the prompt and response in.
        :return:
        """
        if rep_queue is not None and not isinstance(rep_queue, Queue):
            print(f"{Fore.RED}>> Entered a non-queue object to hold responses for another thread.")
            raise Exceptions.PyChatGPTException("Cannot enter a non-queue object as the response queue for threads.")

        # Check if the access token is expired
        if OpenAI.token_expired():
            print(f"{Fore.RED}>> Your access token is expired. {Fore.GREEN}Attempting to recreate it...")
            did_create = self._create_access_token()
            if did_create:
                print(f"{Fore.GREEN}>> Successfully recreated access token.")
            else:
                print(f"{Fore.RED}>> Failed to recreate access token.")
                raise Exceptions.PyChatGPTException("Failed to recreate access token.")
        else:
            print(f"{Fore.GREEN}>> Access token is valid.")
            print(f"{Fore.GREEN}>> Starting CLI chat session...")

        # Get access token
        access_token = OpenAI.get_access_token()

        while True:
            try:
                prompt = input("You: ")
                spinner = Spinner.Spinner()
                spinner.start(Fore.YELLOW + "Chat GPT is typing...")
                answer, previous_convo, convo_id = ChatHandler.ask(auth_token=access_token,
                                                                   prompt=prompt,
                                                                   conversation_id=self.conversation_id,
                                                                   previous_convo_id=self.previous_convo_id,
                                                                   proxies=self.proxies)

                if rep_queue is not None:
                    rep_queue.put((prompt, answer))

                if answer == "400" or answer == "401":
                    print(f"{Fore.RED}>> Failed to get a response from the API.")
                    return None

                self.conversation_id = convo_id
                self.previous_convo_id = previous_convo
                spinner.stop()
                print(f"Chat GPT: {answer}")

                if self.options.save:
                    self.__chat_history.append("You: " + prompt)
                    self.__chat_history.append("Chat GPT: " + answer)

            except KeyboardInterrupt:
                print(f"{Fore.RED}>> Exiting...")
                break
            finally:
                self.save_data()