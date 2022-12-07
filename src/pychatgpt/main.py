#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Builtins
import time
import os

# Local
from .classes import openai as OpenAI
from .classes import chat as ChatHandler
from .classes import spinner as Spinner
from .classes import exceptions as Exceptions

# Fancy stuff
import colorama
from colorama import Fore

colorama.init(autoreset=True)


class Chat:
    def __init__(self, email, password, proxies: str or dict = None, save: bool = False, resume: bool = False, chat_log: str or None = None, id_log: str or None = None):
        self.email = email
        self.password = password
        self.proxies = proxies
	self.save = save
	self.resume = resume
	self.chat_log = chat_log
	self.id_log = id_log

        self.__auth_access_token: str or None = None
        self.__auth_access_token_expiry: int or None = None
        self.__conversation_id: str or None = None
        self.__previous_convo_id: int or None = None
	self.__chat_buf: list or None = None
        self._setup()

    def _setup(self):
        if self.proxies is not None:
            if not isinstance(self.proxies, dict):
                if not isinstance(self.proxies, str):
                    raise Exceptions.PyChatGPTException("Proxies must be a string or dictionary.")
                else:
                    self.proxies = {"http": self.proxies, "https": self.proxies}

        if not self.email or not self.password:
            print(f"{Fore.RED}>> You must provide an email and password when initializing the class.")
            raise Exceptions.PyChatGPTException("You must provide an email and password when initializing the class.")

        if not isinstance(self.email, str) or not isinstance(self.password, str):
            print(f"{Fore.RED}>> Email and password must be strings.")
            raise Exceptions.PyChatGPTException("Email and password must be strings.")

        if len(self.email) == 0 or len(self.password) == 0:
            print(f"{Fore.RED}>> Email and password cannot be empty.")
            raise Exceptions.PyChatGPTException("Email and password cannot be empty.")

	if not isinstance(self.save, bool) or not isinstance(self.resume, bool):
	    print(f"{Fore.RED}>> Options to save and resume must be boolean.")
            raise Exceptions.PyChatGPTException("Options to save and resume must be boolean.")

	if self.save:
		if not self.chat_log or not self.id_log:
			print(f"{Fore.RED}>> You must provide a file path for chat_log and id_log when saving a chat.")
			raise Exceptions.PyChatGPTException("When saving a chat, file paths for chat_log and id_log must be provided.")
		else if not isinstance(self.chat_log, str) or not isinstance(self.id_log, str):
			print(f"{Fore.RED}>> File paths for chat_log and id_log must be strings when saving a chat.")
			raise Exceptions.PyChatGPTException("When saving a chat, file paths for chat_log and id_log must be strings.")
		else if len(self.chat_log) == 0 or len(self.id_log) == 0:
			print(f"{Fore.RED}>> File paths for chat_log and id_log cannot be empty when saving a chat.")
			raise Exceptions.PyChatGPTException("When saving a chat, file paths for chat_log and id_log cannot be empty.")
		else if not os.path.exists(self.chat_log) or not os.path.exists(self.id_log):
			print(f"{Fore.RED}>> File paths for chat_log and id_log must be valid when saving a chat.")
			raise Exceptions.PyChatGPTException("When saving a chat, file paths for chat_log and id_log must already exist.")
		self.__chat_buf = []

	if self.resume and not self.save:
		if self.id_log is None:
			print(f"{Fore.RED}>> You must provide a file path for id_log when resuming a chat.")
			raise Exceptions.PyChatGPTException("When resuming a chat, file path for id_log must be provided.")
		else if not isinstance(self.id_log, str):
			print(f"{Fore.RED}>> File path for id_log must be a string when resuming a chat.")
			raise Exceptions.PyChatGPTException("When resuming a chat, file path for id_log must be a string.")
		else if len(self.id_log) == 0:
			print(f"{Fore.RED}>> File path for id_log cannot be empty when resuming a chat.")
			raise Exceptions.PyChatGPTException("When resuming a chat, file path for id_log cannot be empty.")
		else if not os.path.exists(self.id_log):
			print(f"{Fore.RED}>> File path for id_log must be valid when saving a chat.")	
			raise Exceptions.PyChatGPTException("When resuming a chat, file path for id_log must already exist.")

	if self.resume:
		if os.path.getsize(self.id_log) == 0:
			print(f"{Fore.RED}>> File size for id_log cannot be zero when resuming a chat.")	
			raise Exceptions.PyChatGPTException("When resuming a chat, file size for id_log cannot be zero.")
		else:
			try:
				with open(self.id_log, "r") as f:
					self.__previous_convo_id = int(f.readline().strip())
					self.__conversation_id = int(f.readline().strip())
			except ValueError as verr:
				print(f"{Fore.RED}>> When resuming a chat, conversation id and previous conversation id in id_log must be integers.")	
				raise Exceptions.PyChatGPTException("When resuming a chat, conversation id and previous conversation id in id_log must be integers.")
			except IOError as err:
				print(f"{Fore.RED}>> When resuming a chat, conversation id and previous conversation id in id_log must be separated by newlines.")
				raise Exceptions.PyChatGPTException("When resuming a chat, conversation id and previous conversation id in id_log must be separated by newlines.")
			except Exception as ex:
				print(f"{Fore.RED}>> When resuming a chat, there was an issue reading id_log, make sure that it is formatted correctly.")
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
        openai_auth = OpenAI.Auth(email_address=self.email, password=self.password, proxy=self.proxies)
        openai_auth.create_token()

        # If after creating the token, it's still expired, then something went wrong.
        is_still_expired = OpenAI.token_expired()
        if is_still_expired:
            print(f"{Fore.RED}>> Failed to create access token.")
            return False

        # If created, then return True
        return True

    def ask(self, prompt: str) -> str or None:
        if prompt is None:
            print(f"{Fore.RED}>> Enter a prompt.")
            raise Exceptions.PyChatGPTException("Enter a prompt.")

        if not isinstance(prompt, str):
            raise Exceptions.PyChatGPTException("Prompt must be a string.")

        if len(prompt) == 0:
            raise Exceptions.PyChatGPTException("Prompt cannot be empty.")

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
                                                           conversation_id=self.__conversation_id,
                                                           previous_convo_id=self.__previous_convo_id,
                                                           proxies=self.proxies)
        if answer == "400" or answer == "401":
            print(f"{Fore.RED}>> Failed to get a response from the API.")
            return None

        self.__conversation_id = convo_id
        self.__previous_convo_id = previous_convo
	if self.save:
		self.__chat_buf.append("You: "+prompt)
		self.__chat_buf.append("Chat GPT: "+answer)
        return answer

    def save_data(self):
	if self.save:
		try:
			with open(self.chat_log, "a") as f:
				f.write("\n".join(self.__chat_buf))
			self.__chat_buf = []
			with open(self.id_log, "w") as f:
				f.write(str(self.__previous_convo_id)+"\n")
				f.write(str(self.__conversation_id)+"\n")
		except Exception as ex:
			print(f"{Fore.RED}>> Failed to save chat and ids to chat log and id_log.")

    def cli_chat(self):
        """
        Start a CLI chat session.
        :param prompt:
        :return:
        """
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
                                                                   conversation_id=self.__conversation_id,
                                                                   previous_convo_id=self.__previous_convo_id,
                                                                   proxies=self.proxies)
                if answer == "400" or answer == "401":
                    print(f"{Fore.RED}>> Failed to get a response from the API.")
                    return None

                self.__conversation_id = convo_id
                self.__previous_convo_id = previous_convo
                spinner.stop()
                print(f"Chat GPT: {answer}")
		if self.save:
			self.__chat_buf.append("You: "+prompt)
			self.__chat_buf.append("Chat GPT: "+answer)
            except KeyboardInterrupt:
                print(f"{Fore.RED}>> Exiting...")
		self.save_data()
                break
