from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions as SeleniumExceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

import time

google_oauth_btn = (By.XPATH, '//button[@data-provider="google"]')
microsoft_oauth_btn = (By.XPATH, '//button[@data-provider="windowslive"]')

google_email_input = (By.XPATH, '//input[@type="email"]')
google_next_btn = (By.XPATH, '//*[@id="identifierNext"]')
google_pwd_input = (By.XPATH, '//input[@type="password"]')
google_pwd_next_btn = (By.XPATH, '//*[@id="passwordNext"]')
google_code_samp = (By.TAG_NAME, 'samp')

microsoft_email_input = (By.XPATH, '//input[@type="email"]')
microsoft_pwd_input = (By.XPATH, '//input[@type="password"]')
microsoft_next_btn = (By.XPATH, '//input[@type="submit"]')

openai_email_input = (By.XPATH, '//input[@name="email"]')
openai_pwd_input = (By.XPATH, '//input[@type="password"]')
openai_continue_btn = (By.XPATH, '//button[text()="Continue"]')
openai_captcha_input = (By.XPATH, '//input[@name="captcha"]')
openai_captcha_sitekey = (
    By.XPATH,
    '//div[@data-recaptcha-provider="recaptcha_enterprise"]',
)


def login(self) -> None:
    '''
    Login to ChatGPT
    '''
    if self._ChatGPT__auth_type == 'google':
        __google_login(self)
    elif self._ChatGPT__auth_type == 'microsoft':
        __microsoft_login(self)
    elif self._ChatGPT__auth_type == 'openai':
        __openai_login(self)


def __google_login(self) -> None:
    '''
    Login to ChatGPT using Google
    '''
    self.logger.debug('Clicking Google button...')
    self.driver.find_element(*google_oauth_btn).click()

    google_email_entry = (By.XPATH, f'//div[@data-identifier="{self._ChatGPT__email}"]')
    try:
        self.logger.debug('Checking if Google remembers emai...')

        WebDriverWait(self.driver, 3).until(
            EC.element_to_be_clickable(google_email_entry)
        ).click()
        self.logger.debug('Google remembers email')

    except SeleniumExceptions.TimeoutException:
        self.logger.debug('Google does not remember email')
        self.logger.debug('Entering email...')
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(google_email_input)
        ).send_keys(self._ChatGPT__email)

        self.logger.debug('Clicking Next...')
        self.driver.find_element(*google_next_btn).click()

        self.logger.debug('Entering password...')
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(google_pwd_input)
        ).send_keys(self._ChatGPT__password)

        self.logger.debug('Clicking Next...')
        self.driver.find_element(*google_pwd_next_btn).click()

    try:
        self.logger.debug('Checking if verification code is required...')
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(google_code_samp)
        )
        self.logger.debug('Code is required')
        prev_code = self.driver.find_elements(By.TAG_NAME, 'samp')[0].text
        print('Verification code:', prev_code)
        while True:
            code = self.driver.find_elements(*google_code_samp)
            if not code:
                break
            if code[0].text != prev_code:
                print('Verification code:', code[0].text)
                prev_code = code[0].text
            time.sleep(1)
    except SeleniumExceptions.TimeoutException:
        self.logger.debug('Code is not required')


def __microsoft_login(self) -> None:
    self.logger.debug('Clicking Microsoft button...')
    self.driver.find_element(*microsoft_oauth_btn).click()

    self.logger.debug('Entering email...')
    WebDriverWait(self.driver, 5).until(
        EC.element_to_be_clickable(microsoft_email_input)
    ).send_keys(self._ChatGPT__email)

    self.logger.debug('Clicking Next...')
    self.driver.find_element(*microsoft_next_btn).click()

    self.logger.debug('Entering password...')
    WebDriverWait(self.driver, 5).until(
        EC.element_to_be_clickable(microsoft_pwd_input)
    ).send_keys(self._ChatGPT__password)

    self.logger.debug('Clicking Next...')
    self.driver.find_element(*microsoft_next_btn).click()

    self.logger.debug('Clicking allow...')
    WebDriverWait(self.driver, 5).until(
        EC.element_to_be_clickable(microsoft_next_btn)
    ).click()


def __have_recaptcha_value(self) -> bool:
    '''
    Check if the recaptcha input has a value
    :return: Boolean indicating if the recaptcha input has a value
    '''
    try:
        recaptcha_result = self.driver.find_element(*openai_captcha_input)
        return recaptcha_result.get_attribute('value') != ''
    except SeleniumExceptions.NoSuchElementException:
        return False


def __pypasser_solve(self, retry: int) -> None:
    '''
    Solve the recaptcha using PyPasser
    :param retry: Number of times to retry solving the recaptcha
    '''
    try:
        from pypasser import reCaptchaV2
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            'Please install ffmpeg_downloader, PyPasser, and pocketsphinx by running `pip install ffmpeg_downloader PyPasser pocketsphinx`'
        )

    self.logger.debug(f'Trying pypasser solver, max retry = {retry}')
    try:
        reCaptchaV2(self.driver, False, retry)
    except Exception as e:
        self.logger.debug(f'pypasser solver error: {str(e)}')


def __twocaptcha_solve(self, retry: int) -> None:
    '''
    Solve the recaptcha using 2captcha
    :param retry: Number of times to retry solving the recaptcha
    '''
    try:
        from twocaptcha import TwoCaptcha
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            'Please install twocaptcha by running `pip install 2captcha-python`'
        )

    self.logger.debug(f'Trying 2captcha solver, max retry = {retry}')
    solver = TwoCaptcha(self._ChatGPT__solver_apikey, pollingInterval=5)
    sitekey = self.driver.find_element(*openai_captcha_sitekey).get_attribute(
        'data-recaptcha-sitekey'
    )
    result = None
    for _ in range(retry):
        try:
            result = solver.recaptcha(
                sitekey=sitekey,
                url=self.driver.current_url,
                invisible=1,
                enterprise=1,
            )
            if result:
                captcha_input = self.driver.find_element(*openai_captcha_input)
                self.driver.execute_script(
                    'arguments[0].setAttribute("value", arguments[1])',
                    captcha_input,
                    result['code'],
                )
                break
        except Exception as e:
            self.logger.debug(f'2captcha solver error: {str(e)}')


def __openai_login(self, retry: int = 3) -> None:
    '''
    Login to ChatGPT using OpenAI
    :param retry: Number of times to retry solving the recaptcha
    '''
    self.logger.debug('Entering email...')
    self.driver.find_element(*openai_email_input).send_keys(self._ChatGPT__email)
    self.driver.find_element(*openai_continue_btn).click()

    have_recaptcha = False
    try:
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'iframe[title="reCAPTCHA"]')
            )
        )
        have_recaptcha = True
        self.logger.debug('Captcha detected')
    except SeleniumExceptions.TimeoutException:
        self.logger.debug('No captcha detected')

    try:
        WebDriverWait(self.driver, 3).until(
            EC.text_to_be_present_in_element_attribute(
                openai_captcha_input, 'value', '_'
            )
        )
    except SeleniumExceptions.TimeoutException:
        if self._ChatGPT__captcha_solver == 'pypasser':
            __pypasser_solve(self, retry)
        elif self._ChatGPT__captcha_solver == '2captcha':
            __twocaptcha_solve(self, retry)

    if have_recaptcha:
        if __have_recaptcha_value(self):
            self.logger.debug('Congrat! reCAPTCHA is solved')
        else:
            self.logger.debug('Oops! you need to solve reCAPTCHA manually')
            self.driver.get(self.driver.current_url)
            while not __have_recaptcha_value(self):
                time.sleep(1)

        self.logger.debug('Clicking Continue...')
        self.driver.find_element(*openai_continue_btn).click()

    self.logger.debug('Entering password...')
    self.driver.find_element(*openai_pwd_input).send_keys(self._ChatGPT__password)
    self.driver.find_element(*openai_continue_btn).click()
