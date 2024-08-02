import os
import time 
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import configparser
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LoggerSetup:
    """A class to configure logging with a daily rotating log file.
    """
    def __init__(self, log_directory: str = 'logs') -> None:
        self.log_directory = log_directory
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Sets up logging configuration."""
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

        current_date = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.log_directory,
                                f'{current_date}_evidence_books_logs.log')

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        
        if logger.hasHandlers():
            logger.handlers.clear()
            
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler = TimedRotatingFileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        logger.addHandler(file_handler)

logger = LoggerSetup()
logger = logging.getLogger()

class WebDriverSetup:
    """A class to manage Selenium WebDriver instances based on configuration settings.

    Attributes:
        headless (bool): A flag to indicate whether browsers should be headless.
        nr_instances (int): The number of WebDriver instances to create.
        drivers (List[WebDriver]): A list of initialized WebDriver instances.
    """
    def __init__(self, headless: bool = False, nr_instances: int = 1) -> None:
        self.headless = headless
        self.nr_instances = nr_instances
        self.drivers: List[WebDriver] = []
        
    def create_driver(self) -> WebDriver:
        """Create and configure a Chrome WebDriver instance.

        Returns:
            WebDriver: An initialized Chrome WebDriver instance.
        """
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-profile-{int(time.time())}")
        if self.headless:
            chrome_options.add_argument("--headless")

        return webdriver.Chrome(options=chrome_options)

    @staticmethod 
    def _click_cookies_accept(driver: WebDriver) -> None:
        """Attempt to find and click the 'accept cookies' button.

        Args:
            driver (WebDriver): The WebDriver instance to operate on.
        """
        try:
            accept_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "span.button.close"))
            )
            accept_button.click()
        except Exception as e:
            logger.warning(f"Clicking cookies accept failed with error: {e}")
    
    @staticmethod 
    def _get_url() -> str:
        """Retrieve the URL from a configuration file.

        Returns:
            str: The URL needed for WebDriver operations.
        """
        config = configparser.ConfigParser()
        if not config.read('config.ini'):
            raise FileNotFoundError("Config file 'config.ini' not found.")
        try:
            return str(config['General']['URL'])[1:-1]
        except KeyError as e:
            raise KeyError(f"URL not found in config. Error: {e}")

    def single_driver_setup(self) -> WebDriver:
        """Setup a single WebDriver instance with pre-configured settings and initial navigation.

        Returns:
            WebDriver: The configured WebDriver instance.
        """
        logger.info("Starting WebDriver initialization.")
        try:
            driver = self.create_driver()
            driver.get(self._get_url())
            driver.delete_all_cookies()
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            driver.refresh()
            self._click_cookies_accept(driver)
            return driver
        except Exception as e:
            logger.error(f"WebDriver initialization failed with message: {e}")

    def get_drivers(self) -> List[WebDriver]:
        """Initialize and return a list of WebDriver instances based on the specified number of instances.

        Returns:
            List[WebDriver]: A list of initialized WebDriver instances.
        """
        logger.info(f"Initializing {self.nr_instances} instances")
        self.drivers = [self.single_driver_setup() for _ in range(self.nr_instances)]
        return self.drivers
