#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Builtins
import sys
import time
import os
from queue import Queue
from typing import Tuple

# Local
from .classes import openai as OpenAI
from .classes import chat as ChatHandler
from .classes import spinner as Spinner
from .classes import exceptions as Exceptions

# Fancy stuff
import colorama
from colorama import Fore
from typing import Union
from fastapi import FastAPI, APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI() # A fast api framework
colorama.init(autoreset=True)

class Options:
    def __init__(self):
        self.log: bool = True
        self.proxies: str or dict or None = None
        self.track: bool or None = False
        self.verify: bool = True
        self.chat_log: str or None = None
        self.id_log: str or None = None

class PostItem(BaseModel):
    prompt: str
    conversation: Union[int, None] = None # TODO: conversation

colorama.init(autoreset=True)
# @cbv(router) # to embed api in a class
class Chat:
    def __init__(self,
                 email: str,
                 password: str,
                 options: Options or None = None,
                 conversation_id: str or None = None,
                 previous_convo_id: str or None = None):
        self.email = email
        self.password = password
        self.options = options

        self.conversation_id = conversation_id
        self.previous_convo_id = previous_convo_id

        self.router = APIRouter() # to resolve the issue of fastapi decorations
        self.router.add_api_route("/{prompt}", self.http_get, methods=["GET"])
        self.router.add_api_route("/", self.http_get_default, methods=["GET"])
        self.router.add_api_route("/", self.http_post, methods=["POST"])
        app.include_router(self.router) # manually add the router to the app, althoug not elegant

        self.__auth_access_token: str or None = None
        self.__auth_access_token_expiry: int or None = None
        self.__chat_history: list or None = None

        self._setup()

    @staticmethod
    def _create_if_not_exists(file: str):
        if not os.path.exists(file):
            with open(file, 'w') as f:
                f.write("")

    def log(self, inout):
        if self.options is not None and self.options.log:
            print(inout, file=sys.stderr)

    def _setup(self):
        if self.options is not None:
            # If track is enabled, create the chat log and id log files if they don't exist
            if not isinstance(self.options.track, bool):
                raise Exceptions.PyChatGPTException("Options to track conversation must be a boolean.")
            if not isinstance(self.options.log, bool):
                raise Exceptions.PyChatGPTException("Options to log must be a boolean.")

            if self.options.track:
                if self.options.chat_log is not None:
                    self._create_if_not_exists(os.path.abspath(self.options.chat_log))
                    self.options.chat_log = os.path.abspath(self.options.chat_log)
                else:
                    # Create a chat log file called chat_log.txt
                    self.options.chat_log = "chat_log.txt"
                    self._create_if_not_exists(self.options.chat_log)

                if self.options.id_log is not None:
                    self._create_if_not_exists(os.path.abspath(self.options.id_log))
                    self.options.id_log = os.path.abspath(self.options.id_log)
                else:
                    # Create a chat log file called id_log.txt
                    self.options.id_log = "id_log.txt"
                    self._create_if_not_exists(self.options.id_log)

            if self.options.proxies is not None:
                if not isinstance(self.options.proxies, dict):
                    if not isinstance(self.options.proxies, str):
                        raise Exceptions.PyChatGPTException("Proxies must be a string or dictionary.")
                    else:
                        self.proxies = {"http": self.options.proxies, "https": self.options.proxies}
                        self.log(f"{Fore.GREEN}>> Using proxies: True.")

            if self.options.track:
                self.log(f"{Fore.GREEN}>> Tracking conversation enabled.")
                if not isinstance(self.options.chat_log, str) or not isinstance(self.options.id_log, str):
                    raise Exceptions.PyChatGPTException(
                        "When saving a chat, file paths for chat_log and id_log must be strings.")
                elif len(self.options.chat_log) == 0 or len(self.options.id_log) == 0:
                    raise Exceptions.PyChatGPTException(
                        "When saving a chat, file paths for chat_log and id_log cannot be empty.")

                self.__chat_history = []
        else:
            self.options = Options()


        if not self.email or not self.password:
            self.log(f"{Fore.RED}>> You must provide an email and password when initializing the class.")
            raise Exceptions.PyChatGPTException("You must provide an email and password when initializing the class.")

        if not isinstance(self.email, str) or not isinstance(self.password, str):
            self.log(f"{Fore.RED}>> Email and password must be strings.")
            raise Exceptions.PyChatGPTException("Email and password must be strings.")

        if len(self.email) == 0 or len(self.password) == 0:
            self.log(f"{Fore.RED}>> Email cannot be empty.")
            raise Exceptions.PyChatGPTException("Email cannot be empty.")

        if self.options is not None and self.options.track:
            try:
                with open(self.options.id_log, "r") as f:
                    # Check if there's any data in the file
                    if len(f.read()) > 0:
                        self.previous_convo_id = f.readline().strip()
                        self.conversation_id = f.readline().strip()
                    else:
                        self.conversation_id = None
            except IOError:
                raise Exceptions.PyChatGPTException("When resuming a chat, conversation id and previous conversation id in id_log must be separated by newlines.")
            except Exception:
                raise Exceptions.PyChatGPTException("When resuming a chat, there was an issue reading id_log, make sure that it is formatted correctly.")

        # Check for access_token & access_token_expiry in env
        if OpenAI.token_expired():
            self.log(f"{Fore.RED}>> Access Token missing or expired."
                  f" {Fore.GREEN}Attempting to create them...")
            self._create_access_token()
        else:
            access_token, expiry = OpenAI.get_access_token()
            self.__auth_access_token = access_token
            self.__auth_access_token_expiry = expiry

            try:
                self.__auth_access_token_expiry = int(self.__auth_access_token_expiry)
            except ValueError:
                self.log(f"{Fore.RED}>> Expiry is not an integer.")
                raise Exceptions.PyChatGPTException("Expiry is not an integer.")

            if self.__auth_access_token_expiry < time.time():
                self.log(f"{Fore.RED}>> Your access token is expired. {Fore.GREEN}Attempting to recreate it...")
                self._create_access_token()

    def _create_access_token(self) -> bool:
        openai_auth = OpenAI.Auth(email_address=self.email, password=self.password, proxy=self.options.proxies)
        openai_auth.create_token()

        # If after creating the token, it's still expired, then something went wrong.
        is_still_expired = OpenAI.token_expired()
        if is_still_expired:
            self.log(f"{Fore.RED}>> Failed to create access token.")
            return False

        # If created, then return True
        return True

    def ask(self, prompt: str,
            previous_convo_id: str or None = None,
            conversation_id: str or None = None,
            rep_queue: Queue or None = None
            ) -> Tuple[str or None, str or None, str or None] or None:

        if prompt is None:
            self.log(f"{Fore.RED}>> Enter a prompt.")
            raise Exceptions.PyChatGPTException("Enter a prompt.")

        if not isinstance(prompt, str):
            raise Exceptions.PyChatGPTException("Prompt must be a string.")

        if len(prompt) == 0:
            raise Exceptions.PyChatGPTException("Prompt cannot be empty.")

        if rep_queue is not None and not isinstance(rep_queue, Queue):
            raise Exceptions.PyChatGPTException("Cannot enter a non-queue object as the response queue for threads.")

        # Check if the access token is expired
        if OpenAI.token_expired():
            self.log(f"{Fore.RED}>> Your access token is expired. {Fore.GREEN}Attempting to recreate it...")
            did_create = self._create_access_token()
            if did_create:
                self.log(f"{Fore.GREEN}>> Successfully recreated access token.")
            else:
                self.log(f"{Fore.RED}>> Failed to recreate access token.")
                raise Exceptions.PyChatGPTException("Failed to recreate access token.")

        # Get access token
        access_token = OpenAI.get_access_token()

        # Set conversation IDs if supplied
        if previous_convo_id is not None:
            self.previous_convo_id = previous_convo_id
        if conversation_id is not None:
            self.conversation_id = conversation_id

        answer, previous_convo, convo_id = ChatHandler.ask(auth_token=access_token,
                                                           prompt=prompt,
                                                           conversation_id=self.conversation_id,
                                                           previous_convo_id=self.previous_convo_id,
                                                           proxies=self.options.proxies)

        if rep_queue is not None:
            rep_queue.put((prompt, answer))

        if answer == "400" or answer == "401":
            self.log(f"{Fore.RED}>> Failed to get a response from the API.")
            return None

        self.conversation_id = convo_id
        self.previous_convo_id = previous_convo

        if self.options.track:
            self.__chat_history.append("You: " + prompt)
            self.__chat_history.append("Chat GPT: " + answer)
            self.save_data()

        return answer, previous_convo, convo_id

    def save_data(self):
        if self.options.track:
            try:
                with open(self.options.chat_log, "a") as f:
                    f.write("\n".join(self.__chat_history) + "\n")

                with open(self.options.id_log, "w") as f:
                    f.write(str(self.previous_convo_id) + "\n")
                    f.write(str(self.conversation_id) + "\n")

            except Exception as ex:
                self.log(f"{Fore.RED}>> Failed to save chat and ids to chat log and id_log."
                      f"{ex}")
            finally:
                self.__chat_history = []

    # Respond to HTTP GET requests at /
    async def http_get_default(self) -> JSONResponse:
        """
        GET: "http://host:port/"
        Returns: JSONResponse {
            "error": "Missing query. e.g {host:port/{your_query}"
        }
        """
        return jsonable_encoder({"error": "Missing query. e.g {host:port/{your_query}"})
    
    
    # Respond to HTTP GET requests at /{prompt}
    async def http_get(self, prompt: str) -> JSONResponse:
        """
        #TODO: conversation queue
        GET: "http://host:port/{prompt}"
        Returns: JSONResponse {
            "answer": "{answer}",
            "conversation": "{conversation_id}"
        }
        """
        if prompt is None or len(prompt) == 0 or prompt == " ":
            return jsonable_encoder({"error": "Missing query. e.g {host:port/{your_query}"})
        else:
            print(f"GET: {prompt}")
            answer =  self.ask(prompt)
            if answer is None:
                print(f"{Fore.RED}>> Failed to get a response from the API.")
                return jsonable_encoder({"error": "Failed to get a response from the API."})
            else:
                print(f"Chat GPT: {answer}")
                if self.options.track:
                    self.__chat_history.append("GET: " + prompt)
                    self.__chat_history.append("Chat GPT: " + answer)
                return jsonable_encoder({"answer": answer, "conversation":self.conversation_id})
    
    # Respond to HTTP POST requests
    async def http_post(self, request: PostItem) -> JSONResponse:
        """
        #TODO: conversation queue
        POST: "http://host:port/" with a application/json {
            "prompt": "{prompt}",
            "conversation": "{conversation_id}" (optional)
            }
        Returns: JSONResponse {
            "answer": "{answer}",
            "conversation": "{conversation_id}"
        }
        """
        prompt = request.prompt
        if prompt is None or len(prompt) == 0 or prompt == " ":
            return jsonable_encoder({"error": "Missing or invalid query. e.g POST {'prompt': 'your query'} to host:port"})
        else:
            print(f"POST: {prompt}")
            answer =  self.ask(prompt)
            if answer is None:
                print(f"{Fore.RED}>> Failed to get a response from the API.")
                return jsonable_encoder({"error": "Failed to get a response from the API."})
            else:
                print(f"Chat GPT: {answer}")
                if self.options.track:
                    self.__chat_history.append("POST: " + prompt)
                    self.__chat_history.append("Chat GPT: " + answer)
                return jsonable_encoder({"answer": answer, "conversation": self.conversation_id})

    def server_chat(self, host:str="127.0.0.1", port:int=8000)->None:
        """
        Start a CLI chat session.
        :param rep_queue:  A queue to put the prompt and response in.
        :return:
        """
        print(f"{Fore.GREEN}>> Server running at {host}:{port}...")
        uvicorn.run(app, host=host, port=port)

    def cli_chat(self, rep_queue: Queue or None = None):
        """
        Start a CLI chat session.
        :param rep_queue:  A queue to put the prompt and response in.
        :return:
        """
        if rep_queue is not None and not isinstance(rep_queue, Queue):
            self.log(f"{Fore.RED}>> Entered a non-queue object to hold responses for another thread.")
            raise Exceptions.PyChatGPTException("Cannot enter a non-queue object as the response queue for threads.")

        # Check if the access token is expired
        if OpenAI.token_expired():
            self.log(f"{Fore.RED}>> Your access token is expired. {Fore.GREEN}Attempting to recreate it...")
            did_create = self._create_access_token()
            if did_create:
                self.log(f"{Fore.GREEN}>> Successfully recreated access token.")
            else:
                self.log(f"{Fore.RED}>> Failed to recreate access token.")
                raise Exceptions.PyChatGPTException("Failed to recreate access token.")
        else:
            self.log(f"{Fore.GREEN}>> Access token is valid.")
            self.log(f"{Fore.GREEN}>> Starting CLI chat session...")
            self.log(f"{Fore.GREEN}>> Type 'exit' to exit the chat session.")


        # Get access token
        access_token = OpenAI.get_access_token()

        while True:
            try:
                prompt = input("You: ")
                if prompt.replace("You: ", "") == "exit":
                    self.save_data()
                    break

                spinner = Spinner.Spinner()
                spinner.start(Fore.YELLOW + "Chat GPT is typing...")
                answer, previous_convo, convo_id = ChatHandler.ask(auth_token=access_token,
                                                                   prompt=prompt,
                                                                   conversation_id=self.conversation_id,
                                                                   previous_convo_id=self.previous_convo_id,
                                                                   proxies=self.options.proxies)

                if rep_queue is not None:
                    rep_queue.put((prompt, answer))

                if answer == "400" or answer == "401":
                    self.log(f"{Fore.RED}>> Failed to get a response from the API.")
                    return None

                self.conversation_id = convo_id
                self.previous_convo_id = previous_convo
                spinner.stop()
                print(f"Chat GPT: {answer}")

                if self.options.track:
                    self.__chat_history.append("You: " + prompt)
                    self.__chat_history.append("Chat GPT: " + answer)

            except KeyboardInterrupt:
                print(f"{Fore.RED}>> Exiting...")
                break
            finally:
                self.save_data()
