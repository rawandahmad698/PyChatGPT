from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions as SeleniumExceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
from markdownify import markdownify
from threading import Thread
import logging
import weakref
import json
import time
import re
import os
import requests
from pathlib import Path

cf_challenge_form = (By.ID, 'challenge-form')

chatgpt_textbox = (By.XPATH, '//div[@id="prompt-textarea"]')
chatgpt_alert = (By.XPATH, '//div[@role="alert"]')
chatgpt_intro = (By.ID, 'headlessui-portal-root')
chatgpt_logged_h1 = (By.XPATH, '(//div[@class="text-token-text-secondary" and text()="ChatGPT"])[1]')

chatgpt_chat_url = 'https://chatgpt.com'


class ChatGPT:
    '''
    An unofficial Python wrapper for OpenAI's ChatGPT API
    Updated code by Prathmesh Soni
    '''
    def __init__(
            self,
            session_token: str = None,
            conversation_id: str = '',
            login_cookies_path: str = '',
            captcha_solver: str = 'pypasser',
            solver_apikey: str = '',
            proxy: str = None,
            chrome_args: list = [],
            moderation: bool = True,
            verbose: bool = False,
    ):
        '''
        Initialize the ChatGPT object\n
        :param session_token: The session token to use for authentication
        :param conversation_id: The conversation ID to use for the chat session
        :param auth_type: The authentication type to use (`google`, `microsoft`, `openai`)
        :param email: The email to use for authentication
        :param password: The password to use for authentication
        :param login_cookies_path: The path to the cookies file to use for authentication
        :param captcha_solver: The captcha solver to use (`pypasser`, `2captcha`)
        :param solver_apikey: The apikey of the captcha solver to use (if any)
        :param proxy: The proxy to use for the browser (`https://ip:port`)
        :param chrome_args: The arguments to pass to the browser
        :param moderation: Whether to enable message moderation
        :param verbose: Whether to enable verbose logging
        '''
        self.__init_logger(verbose)

        self.__session_token = session_token
        self.__conversation_id = conversation_id if conversation_id else 'new'
        self.__auth_type = "openai"
        self.__login_cookies_path = login_cookies_path
        self.__captcha_solver = captcha_solver
        self.__solver_apikey = solver_apikey
        self.__proxy = proxy
        self.__chrome_args = chrome_args
        self.__moderation = moderation
        self.logs_file = Path(__file__).parent / 'logs.txt'
        self.response_folder = Path(__file__).parent / 'chat/chat'
        self.chat_count = 1

        if self.__auth_type not in [None, 'google', 'microsoft', 'openai']:
            raise ValueError('Invalid authentication type')
        if self.__captcha_solver not in [None, 'pypasser', '2captcha']:
            raise ValueError('Invalid captcha solver')
        if self.__captcha_solver == '2captcha' and not self.__solver_apikey:
            raise ValueError('Please provide a 2captcha apikey')
        if self.__proxy and not re.findall(
            r'(https?|socks(4|5)?):\/\/.+:\d{1,5}', self.__proxy
        ):
            raise ValueError('Invalid proxy format')
        if self.__auth_type == 'openai' and self.__captcha_solver == 'pypasser':
            try:
                import ffmpeg_downloader as ffdl
            except ModuleNotFoundError:
                raise ValueError(
                    'Please install ffmpeg_downloader, PyPasser, and pocketsphinx by running `pip install ffmpeg_downloader PyPasser pocketsphinx`'
                )

            ffmpeg_installed = bool(ffdl.ffmpeg_version)
            self.logger.debug(f'ffmpeg installed: {ffmpeg_installed}')
            if not ffmpeg_installed:
                import subprocess

                subprocess.run(['ffdl', 'install'])
            os.environ['PATH'] += os.pathsep + ffdl.ffmpeg_dir

        self.__init_browser()
        weakref.finalize(self, self.__del__)
        self.clear_conventions()

    def __del__(self):
        '''
        Close the browser and display
        '''
        self.__is_active = False
        if hasattr(self, 'driver'):
            self.logger.debug('Closing browser...')
            self.driver.quit()
        if hasattr(self, 'display'):
            self.logger.debug('Closing display...')
            self.display.stop()

    def __init_logger(self, verbose: bool) -> None:
        '''
        Initialize the logger\n
        :param verbose: Whether to enable verbose logging
        '''
        self.logger = logging.getLogger('pyChatGPT')
        self.logger.setLevel(logging.DEBUG)
        if verbose:
            formatter = logging.Formatter('[%(funcName)s] %(message)s')
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def __init_browser(self) -> None:
        '''
        Initialize the browser
        '''

        self.logger.debug('Initializing browser...')
        options = Options() # Updated code by Prathmesh Soni
        options.add_argument('--window-size=1024,768')
        
        '''
            Add the path of the profile directory to make one time login in chatgpt
        '''
        profile_path = "D:\\PycharmProjects\\meet\\prathmesh-demo\\Profile 1"
        options.add_argument(f"--user-data-dir={profile_path}")
        '''
            headless mode is disabled due to cloudflare captcha issue
        '''
        # options.add_argument('--headless')
        
        if self.__proxy:
            options.add_argument(f'--proxy-server={self.__proxy}')
        for arg in self.__chrome_args:
            options.add_argument(arg)
        try:
            self.driver = uc.Chrome(options=options)
        except TypeError as e:
            if str(e) == 'expected str, bytes or os.PathLike object, not NoneType':
                raise ValueError('Chrome installation not found')
            raise e

        if self.__login_cookies_path and os.path.exists(self.__login_cookies_path):
            self.logger.debug('Restoring cookies...')
            try:
                with open(self.__login_cookies_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    if cookie['name'] == '__Secure-next-auth.session-token':
                        self.__session_token = cookie['value']
            except json.decoder.JSONDecodeError:
                self.logger.debug(f'Invalid cookies file: {self.__login_cookies_path}')

        if self.__session_token:
            self.logger.debug('Restoring session_token...')
            self.driver.execute_cdp_cmd(
                'Network.setCookie',
                {
                    'domain': 'chat.openai.com',
                    'path': '/',
                    'name': '__Secure-next-auth.session-token',
                    'value': self.__session_token,
                    'httpOnly': True,
                    'secure': True,
                },
            )

        if not self.__moderation:
            self.logger.debug('Blocking moderation...')
            self.driver.execute_cdp_cmd(
                'Network.setBlockedURLs',
                {'urls': ['https://chat.openai.com/backend-api/moderations']},
            )

        self.logger.debug('Ensuring Cloudflare cookies...')
        self.__ensure_cf()

        self.logger.debug('Opening chat page...')
        self.driver.get(f'{chatgpt_chat_url}/c/{self.__conversation_id}')
        self.__check_blocking_elements()

        self.__is_active = True
        Thread(target=self.__keep_alive, daemon=True).start()

    def __ensure_cf(self, retry: int = 3) -> None:
        '''
        Ensure Cloudflare cookies are set\n
        :param retry: Number of retries
        '''
        self.logger.debug('Opening new tab...')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        self.logger.debug('Getting Cloudflare challenge...')
        self.driver.get('https://chat.openai.com/api/auth/session')
        try:
            WebDriverWait(self.driver, 10).until_not(
                EC.presence_of_element_located(cf_challenge_form)
            )
        except SeleniumExceptions.TimeoutException:
            self.logger.debug(f'Cloudflare challenge failed, retrying {retry}...')
            self.driver.save_screenshot(f'cf_failed_{retry}.png')
            if retry > 0:
                self.logger.debug('Closing tab...')
                self.driver.close()
                self.driver.switch_to.window(original_window)
                return self.__ensure_cf(retry - 1)
            raise ValueError('Cloudflare challenge failed')
        self.logger.debug('Cloudflare challenge passed')

        self.logger.debug('Validating authorization...')
        response = self.driver.page_source
        if response[0] != '{':
            response = self.driver.find_element(By.TAG_NAME, 'pre').text
        response = json.loads(response)
        if (not response) or (
            'error' in response and response['error'] == 'RefreshAccessTokenError'
        ):
            self.logger.debug('Authorization is invalid')
            if not self.__auth_type:
                raise ValueError('Invalid session token')
            self.__login()
        self.logger.debug('Authorization is valid')

        self.logger.debug('Closing tab...')
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def __check_capacity(self, target_url: str):
        '''
        Check if ChatGPT is at capacity\n
        :param target_url: URL to retry if ChatGPT is at capacity
        '''
        while True:
            try:
                self.logger.debug('Checking if ChatGPT is at capacity...')
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[text()="ChatGPT is at capacity right now"]')
                    )
                )
                self.logger.debug('ChatGPT is at capacity, retrying...')
                self.driver.get(target_url)
            except SeleniumExceptions.TimeoutException:
                self.logger.debug('ChatGPT is not at capacity')
                break

    def __login(self) -> None:
        '''
        Login to ChatGPT
        '''
        self.logger.debug('Opening new tab...')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        self.logger.debug('Opening login page...')
        self.driver.get('https://chat.openai.com/auth/login')
        self.__check_capacity('https://chat.openai.com/auth/login')

        self.logger.debug('Clicking login button...')
        '''
            Only for one time login in chatgpt using profile directory 
        '''
        input('If Login successFull then press enter : ')

        self.logger.debug('Checking if login was successful')
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(chatgpt_logged_h1)
            )
            if self.__login_cookies_path:
                self.logger.debug('Saving cookies...')
                with open(self.__login_cookies_path, 'w', encoding='utf-8') as f:
                    json.dump(
                        [
                            i
                            for i in self.driver.get_cookies()
                            if i['name'] == '__Secure-next-auth.session-token'
                        ],
                        f,
                    )
        except SeleniumExceptions.TimeoutException as e:
            self.driver.save_screenshot('login_failed.png')
            raise e

        self.logger.debug('Closing tab...')
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def __keep_alive(self) -> None:
        '''
        Keep the session alive by updating the local storage\n
        Credit to Rawa#8132 in the ChatGPT Hacking Discord server
        '''
        while self.__is_active:
            self.logger.debug('Updating session...')
            payload = (
                '{"event":"session","data":{"trigger":"getSession"},"timestamp":%d}'
                % int(time.time())
            )
            try:
                self.driver.execute_script(
                    'window.localStorage.setItem("nextauth.message", arguments[0])',
                    payload,
                )
            except Exception as e:
                self.logger.debug(f'Failed to update session: {str(e)}')
            time.sleep(60)

    def __check_blocking_elements(self) -> None:
        '''
        Check for blocking elements and dismiss them
        '''
        self.logger.debug('Looking for blocking elements...')
        try:
            intro = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located(chatgpt_intro)
            )
            self.logger.debug('Dismissing intro...')
            self.driver.execute_script('arguments[0].remove()', intro)
        except SeleniumExceptions.TimeoutException:
            pass

        alerts = self.driver.find_elements(*chatgpt_alert)
        if alerts:
            self.logger.debug('Dismissing alert...')
            self.driver.execute_script('arguments[0].remove()', alerts[0])

    # Updated code by Prathmesh Soni
    def clear_conventions(self):
        self.driver.execute_script(
            '''
                document.querySelectorAll('div article').forEach(all =>{
                    all.remove();
                })
                document.querySelectorAll('#prompt-textarea p').forEach((all, index) =>{
                     if (index !== 0) {
                         all.remove();
                     }
                 })

                document.querySelector('#prompt-textarea p').innerHTML = '';
            '''
        )
        time.sleep(1)
    
    # Updated code by Prathmesh Soni
    def send_message(self, message: str, stream: bool = False) -> dict:
        try:
            if 'c/' in self.driver.current_url:
                self.__conversation_id = self.driver.current_url.split('c/')[-1].replace('/', '')
        except:
            pass
        '''
        Send a message to ChatGPT\n
        :param message: Message to send
        :return: Dictionary with keys `message` and `conversation_id`
        
        Updated code by Prathmesh Soni
        '''
        self.__ensure_cf()
        textbox = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(chatgpt_textbox)
        )
        textbox.click()
        time.sleep(0.2)
        self.print('click on text')
        textbox.send_keys(message)

        send_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="send-button"]'))
        )
        send_btn.click()
        self.print('click on send')

        time.sleep(0.2)
        
        co = 0
        demo_text = ''
        while True:
            try:
                nc = self.driver.find_elements(
                    By.XPATH,
                    '//article//div[@data-message-author-role="assistant"]//div[starts-with(@class, "markdown")]'
                )
                demo_text = markdownify(nc[0].get_attribute('innerHTML')).replace(
                    'Copy code`', '`'
                )
                break
            except:
                pass
            if co == 24:
                try:
                    send_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="stop-button"]'))
                    )
                    send_btn.click()
                except:
                    pass
            if co == 25:
                break
            self.print(co)
            co += 1
            time.sleep(1)

        try:
            textbox_text = self.get_texts()
        except:
            textbox_text = demo_text

        self.print(textbox_text, f'{self.response_folder}_{self.chat_count}.md')
        self.clear_conventions()
        self.chat_count += 1
        return {'message': textbox_text}

    # Updated code by Prathmesh Soni
    def get_texts(self):
        try:
            if 'c/' not in self.driver.current_url:
                time.sleep(2.5)
            self.__conversation_id = self.driver.current_url.split('c/')[-1].replace('/', '')
        except:
            pass
        url = f"https://chatgpt.com/backend-api/conversation/{self.__conversation_id}"

        payload = {}
        cookies = {}
        for i in self.driver.get_cookies():
            try:
                cookies[i['name']] = i['value']
            except:
                pass
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': 'Bearer',
            'oai-device-id': '511b6311-0dd4-4455-94df-176e79497625',
            'oai-language': 'en-US',
            'priority': 'u=1, i',
            'referer': f'https://chatgpt.com/c/{self.__conversation_id}',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        }
        response = requests.request("GET", url, cookies=cookies, headers=headers, data=payload)

        aa = response.json()['mapping']
        lasts = list(aa.keys())[-1]
        s = response.json()['mapping'][lasts]['message']['content']['parts']
        return s[0]

    # Updated code by Prathmesh Soni
    def print(self, text, file_name=None):
        if file_name:
            with open(file_name, 'a', encoding='utf-8') as f:
                f.write(f'{text}\n')

            return

        with open(self.logs_file, 'a') as f:
            f.write(f'{text}\n')

    def refresh_chat_page(self) -> None:
        '''
        Refresh the chat page
        '''
        if not self.driver.current_url.startswith(chatgpt_chat_url):
            return self.logger.debug('Current URL is not chat page, skipping refresh')

        self.driver.get(chatgpt_chat_url)
        self.__check_capacity(chatgpt_chat_url)
        self.__check_blocking_elements()
