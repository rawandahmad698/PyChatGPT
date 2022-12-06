# Builtins
import json
import os
import time
import urllib.parse
from io import BytesIO
import re
import base64
from typing import Tuple

# Client (Thank you!.. https://github.com/FlorianREGAZ)
import tls_client

# BeautifulSoup
from bs4 import BeautifulSoup

# Svg lib
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

# Local
from . import exceptions as Exceptions

# Fancy stuff
import colorama
from colorama import Fore

colorama.init(autoreset=True)


def token_expired() -> bool:
    """
        Check if the creds have expired
        returns:
            bool: True if expired, False if not
    """
    try:
        # Get path using os, it's in ./classes/auth.json
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, "auth.json")

        with open(path, 'r') as f:
            creds = json.load(f)
            expires_at = float(creds['expires_at'])
            if time.time() > expires_at + 3600:
                return True
            else:
                return False
    except FileNotFoundError:
        return True


def get_access_token() -> Tuple[str or None, str or None]:
    """
        Get the access token
        returns:
            str: The access token
    """
    try:
        # Get path using os, it's in ./Classes/auth.json
        path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(path, "auth.json")

        with open(path, 'r') as f:
            creds = json.load(f)
            return creds['access_token'], creds['expires_at']
    except FileNotFoundError:
        return None, None


class Auth:
    def __init__(self, email_address: str, password: str, proxy: str = None):
        self.email_address = email_address
        self.password = password
        self.proxy = proxy
        self.__session = tls_client.Session(
            client_identifier="chrome_105"
        )

    @staticmethod
    def _url_encode(string: str) -> str:
        """
        URL encode a string
        :param string:
        :return:
        """
        return urllib.parse.quote(string)

    def create_token(self):
        """
            Begin the auth process
        """
        if not self.email_address or not self.password:
            print(f"{Fore.RED}[OpenAI] {Fore.WHITE}Please provide an email address and password")
            raise Exceptions.PyChatGPTException("Please provide an email address and password")
        else:
            # Print email address and password
            print(f"{Fore.GREEN}[OpenAI] {Fore.WHITE}Email address: {self.email_address}")
            # Show 3 characters of password, then hide the rest
            print(f"{Fore.GREEN}[OpenAI] {Fore.WHITE}Password: {self.password[:3]}{'*' * len(self.password[3:])}")

            if self.proxy is not None:
                if isinstance(self.proxy, str):
                    proxies = {
                        "http": self.proxy,
                        "https": self.proxy
                    }
                else:
                    proxies = self.proxy
                print(f"{Fore.GREEN}[OpenAI] {Fore.WHITE}Using proxy: {self.proxy}")
                self.__session.proxies = proxies

        print(f"{Fore.GREEN}[OpenAI] {Fore.WHITE}Beginning auth process")
        # First, make a request to https://chat.openai.com/auth/login
        url = "https://chat.openai.com/auth/login"
        headers = {
            "Host": "ask.openai.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        print(f"{Fore.GREEN}[OpenAI][1] {Fore.WHITE}Making request to {url}")

        response = self.__session.get(url=url, headers=headers)
        if response.status_code == 200:
            print(f"{Fore.GREEN}[OpenAI][1] {Fore.WHITE}Request was " + Fore.GREEN + "successful")
            self._part_two()
        else:
            raise Exceptions.Auth0Exception("Failed to make the first request, Try that again!")

    def _part_two(self):
        """
        In part two, We make a request to https://chat.openai.com/api/auth/csrf and grab a fresh csrf token
        """

        print(f"{Fore.GREEN}[OpenAI][2] {Fore.WHITE}Beginning part two")
        url = "https://chat.openai.com/api/auth/csrf"
        headers = {
            "Host": "ask.openai.com",
            "Accept": "*/*",
            "Connection": "keep-alive",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Referer": "https://chat.openai.com/auth/login",
            "Accept-Encoding": "gzip, deflate, br",
        }
        print(f"{Fore.GREEN}[OpenAI][2] {Fore.WHITE}Grabbing CSRF token from {url}")
        response = self.__session.get(url=url, headers=headers)
        if response.status_code == 200 and 'json' in response.headers['Content-Type']:
            print(f"{Fore.GREEN}[OpenAI][2] {Fore.WHITE}Request was " + Fore.GREEN + "successful")
            csrf_token = response.json()["csrfToken"]
            print(f"{Fore.GREEN}[OpenAI][2] {Fore.WHITE}CSRF Token: {csrf_token}")
            self._part_three(token=csrf_token)
        else:
            raise Exceptions.Auth0Exception("[OpenAI][2] Failed to make the request, Try that again!")

    def _part_three(self, token: str):
        """
        We reuse the token from part to make a request to /api/auth/signin/auth0?prompt=login
        """
        print(f"{Fore.GREEN}[OpenAI][3] {Fore.WHITE}Beginning part three")
        url = "https://chat.openai.com/api/auth/signin/auth0?prompt=login"

        payload = f'callbackUrl=%2F&csrfToken={token}&json=true'
        headers = {
            'Host': 'ask.openai.com',
            'Origin': 'https://chat.openai.com',
            'Connection': 'keep-alive',
            'Accept': '*/*',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Referer': 'https://chat.openai.com/auth/login',
            'Content-Length': '100',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        print(f"{Fore.GREEN}[OpenAI][3] {Fore.WHITE}Making request to {url}")
        response = self.__session.post(url=url, headers=headers, data=payload)
        if response.status_code == 200 and 'json' in response.headers['Content-Type']:
            print(f"{Fore.GREEN}[OpenAI][3] {Fore.WHITE}Request was " + Fore.GREEN + "successful")
            url = response.json()["url"]
            print(f"{Fore.GREEN}[OpenAI][3] {Fore.WHITE}Callback URL: {url}")
            self._part_four(url=url)
        elif response.status_code == 400:
            raise Exceptions.IPAddressRateLimitException("[OpenAI][3] Bad request from your IP address, "
                                                         "try again in a few minutes")
        else:
            raise Exceptions.Auth0Exception("[OpenAI][3] Failed to make the request, Try that again!")

    def _part_four(self, url: str):
        """
        We make a GET request to url
        :param url:
        :return:
        """
        headers = {
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://chat.openai.com/',
        }
        print(f"{Fore.GREEN}[OpenAI][4] {Fore.WHITE}Making request to {url}")
        response = self.__session.get(url=url, headers=headers)
        if response.status_code == 302:
            print(f"{Fore.GREEN}[OpenAI][4] {Fore.WHITE}Request was " + Fore.GREEN + "successful")
            state = re.findall(r"state=(.*)", response.text)[0]
            state = state.split('"')[0]
            print(f"{Fore.GREEN}[OpenAI][4] {Fore.WHITE}Current State: {state}")
            self._part_five(state=state)
        else:
            raise Exceptions.Auth0Exception("[OpenAI][4] Failed to make the request, Try that again!")

    def _part_five(self, state: str):
        """
        We use the state to get the login page & check for a captcha
        """
        url = f"https://auth0.openai.com/u/login/identifier?state={state}"

        headers = {
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://chat.openai.com/',
        }
        print(f"{Fore.GREEN}[OpenAI][5] {Fore.WHITE}Making request to {url}")
        response = self.__session.get(url, headers=headers)
        if response.status_code == 200:
            print(f"{Fore.GREEN}[OpenAI][5] {Fore.WHITE}Request was " + Fore.GREEN + "successful")
            soup = BeautifulSoup(response.text, 'lxml')
            if soup.find('img', alt='captcha'):
                print(f"{Fore.RED}[OpenAI][5] {Fore.RED}Captcha detected")

                svg_captcha = soup.find('img', alt='captcha')['src'].split(',')[1]
                decoded_svg = base64.decodebytes(svg_captcha.encode("ascii"))

                # Convert decoded svg to png
                drawing = svg2rlg(BytesIO(decoded_svg))

                # Better quality
                renderPM.drawToFile(drawing, "captcha.png", fmt="PNG", dpi=300)
                print(f"{Fore.GREEN}[OpenAI][5] {Fore.WHITE}Captcha saved to {Fore.GREEN}captcha.png"
                      + f" {Fore.WHITE}in the current directory")

                # Wait.
                captcha_input = input(f"{Fore.GREEN}[OpenAI][5] {Fore.WHITE}Please solve the captcha and "
                                      f"press enter to continue: ")
                if captcha_input:
                    print(f"{Fore.GREEN}[OpenAI][5] {Fore.WHITE}Continuing...")
                    self._part_six(state=state, captcha=captcha_input)
                else:
                    raise Exceptions.PyChatGPTException("[OpenAI][5] You didn't enter anything.")

            else:
                print(f"{Fore.GREEN}[OpenAI][5] {Fore.GREEN}No captcha detected")
                self._part_six(state=state, captcha=None)
        else:
            raise Exceptions.Auth0Exception("[OpenAI][5] Failed to make the request, Try that again!")

    def _part_six(self, state: str, captcha: str or None):
        """
        We make a POST request to the login page with the captcha, email
        :param state:
        :param captcha:
        :return:
        """
        print(f"{Fore.GREEN}[OpenAI][6] {Fore.WHITE}Making request to https://auth0.openai.com/u/login/identifier")
        url = f"https://auth0.openai.com/u/login/identifier?state={state}"
        email_url_encoded = self._url_encode(self.email_address)
        payload = f'state={state}&username={email_url_encoded}&captcha={captcha}&js-available=true&webauthn-available=true&is-brave=false&webauthn-platform-available=true&action=default'

        if captcha is None:
            payload = f'state={state}&username={email_url_encoded}&js-available=false&webauthn-available=true&is-brave=false&webauthn-platform-available=true&action=default'

        headers = {
            'Host': 'auth0.openai.com',
            'Origin': 'https://auth0.openai.com',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Referer': f'https://auth0.openai.com/u/login/identifier?state={state}',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.__session.post(url, headers=headers, data=payload)
        if response.status_code == 302:
            print(f"{Fore.GREEN}[OpenAI][6] {Fore.WHITE}Email found")
            self._part_seven(state=state)
        else:
            raise Exceptions.Auth0Exception("[OpenAI][6] Email not found, Check your email address and try again!")

    def _part_seven(self, state: str):
        """
        We enter the password
        :param state:
        :return:
        """
        print(f"{Fore.GREEN}[OpenAI][7] {Fore.WHITE}Entering password...")
        url = f"https://auth0.openai.com/u/login/password?state={state}"

        email_url_encoded = self._url_encode(self.email_address)
        password_url_encoded = self._url_encode(self.password)
        payload = f'state={state}&username={email_url_encoded}&password={password_url_encoded}&action=default'
        headers = {
            'Host': 'auth0.openai.com',
            'Origin': 'https://auth0.openai.com',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Referer': f'https://auth0.openai.com/u/login/password?state={state}',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.__session.post(url, headers=headers, data=payload)
        is_302 = response.status_code == 302
        if is_302:
            print(f"{Fore.GREEN}[OpenAI][7] {Fore.WHITE}Password was " + Fore.GREEN + "correct")
            new_state = re.findall(r"state=(.*)", response.text)[0]
            new_state = new_state.split('"')[0]
            print(f"{Fore.GREEN}[OpenAI][7] {Fore.WHITE}Old state: {Fore.GREEN}{state}")
            print(f"{Fore.GREEN}[OpenAI][7] {Fore.WHITE}New State: {Fore.GREEN}{new_state}")
            self._part_eight(old_state=state, new_state=new_state)
        else:
            raise Exceptions.Auth0Exception("[OpenAI][7] Password was incorrect or captcha was wrong")

    def _part_eight(self, old_state: str, new_state):
        url = f"https://auth0.openai.com/authorize/resume?state={new_state}"
        print(f"{Fore.GREEN}[OpenAI][8] {Fore.WHITE}Making request to {Fore.GREEN}{url}")
        headers = {
            'Host': 'auth0.openai.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Referer': f'https://auth0.openai.com/u/login/password?state={old_state}',
        }
        response = self.__session.get(url, headers=headers, allow_redirects=True)
        is_200 = response.status_code == 200
        if is_200:
            print(f"{Fore.GREEN}[OpenAI][8] {Fore.WHITE}All good")
            soup = BeautifulSoup(response.text, 'lxml')
            # Find __NEXT_DATA__, which contains the data we need, the get accessToken
            next_data = soup.find("script", {"id": "__NEXT_DATA__"})
            # Access Token
            access_token = re.findall(r"accessToken\":\"(.*)\"", next_data.text)
            if access_token:
                access_token = access_token[0]
                access_token = access_token.split('"')[0]
                print(f"{Fore.GREEN}[OpenAI][8] {Fore.WHITE}Access Token: {Fore.GREEN}{access_token}")
                # Save access_token
                self.save_access_token(access_token=access_token)
            else:
                raise Exceptions.Auth0Exception("[OpenAI][8] While most of the process was successful, "
                                                "Auth0 didn't issue an access token, Use proxies or retry.")

    @staticmethod
    def save_access_token(access_token: str, expiry: int or None = None):
        """
        Save access_token and an hour from now on CHATGPT_ACCESS_TOKEN CHATGPT_ACCESS_TOKEN_EXPIRY environment variables
        :param expiry:
        :param access_token:
        :return:
        """
        try:
            print(f"{Fore.GREEN}[OpenAI][9] {Fore.WHITE}Saving access token...")
            expiry = expiry or int(time.time()) + 3600

            # Get path using os, it's in ./classes/auth.json
            path = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(path, "auth.json")
            with open(path, "w") as f:
                f.write(json.dumps({"access_token": access_token, "expires_at": expiry}))

            print(f"{Fore.GREEN}[OpenAI][8] {Fore.WHITE}Saved access token")
        except Exception as e:
            raise e
