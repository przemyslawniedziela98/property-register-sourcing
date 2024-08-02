import re
import time 
import configparser
import logging
import threading
import queue
from typing import Dict, List, Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
)

import setup 
import database


setup.LoggerSetup()
logger = logging.getLogger()
db = database.MongoDBHandler()
element_exp = lambda id_, driver: driver.find_element(By.ID, id_)


def get_config() -> Dict[str, Any]:
    """Retrieve configuration settings from 'config.ini'.

    Returns:
        Dict[str, Union[str, int, float]]: The configuration settings from the 'Sourcing config' section.
    """
    config = configparser.ConfigParser()
    if not config.read('config.ini'):
        raise FileNotFoundError("Config file 'config.ini' not found.")
    
    try:
        return config['Sourcing config']
    except KeyError as e:
        raise KeyError(f"Section not found in config. Error: {e}")


def get_department_codes(driver: WebDriver) -> List[str]:
    """Fetch department codes from dropdown

    Args:
        driver (WebDriver): The Selenium WebDriver instance.

    Returns:
        List[str]: A list of department codes found in the dropdown element.
    """
    try:
        element_exp('kodWydzialuImg', driver).click()

        dropdown_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'kodWydzialuList'))
        )
        return re.findall(r"(?<=\n)[A-Z]{2}\d[A-Z](?= - )", dropdown_element.text)
    except Exception as e:
        logger.warning(f"Failed to get department codes with exception: {e}.")
        return []


class EvidenceBook:
    """A class to interact with a legal evidence book using a web-based system.

    Attributes:
        driver (WebDriver): Selenium WebDriver instance.
        department_code (str): The department code for book identification.
        url (str): The URL of the web page to interact with.
        sleep (int): Duration to sleep between actions, retrieved from config.
    """

    def __init__(self, driver: WebDriver, department_code: str, url: str) -> None:
        self.driver = driver
        self.department_code = department_code
        self.url = url
        self.sleep = int(get_config().get('ERROR_SLEEP', 300))  

    @staticmethod
    def __char_value(char: str) -> int:
        return "0123456789XABCDEFGHIJKLMNOPRSTUWYZ".index(char)

    def get_control_number(self, department_code: str, number: str) -> int:
        """Calculate the control number for a given department code and number.

        Args:
            department_code (str): The department code.
            number (str): The book number.

        Returns:
            int: Calculated control number.
        """
        full_number = department_code + number
        weights = [1, 3, 7] * ((len(full_number) + 2) // 3) 
        total_sum = sum(self.__char_value(char) * weights[i] for i, char in enumerate(full_number))
        return total_sum % 10
    
    @staticmethod
    def get_land_register_info_from_metadata(metadata: str) -> Dict[str, str]:
        """Extract land register information from metadata.

        Args:
            metadata (str): The metadata containing information.

        Returns:
            Dict[str, str]: Extracted land register information.
        """
        extracted_metadata = {}
        columns = [
            'Numer księgi wieczystej',
            'Typ księgi wieczystej',
            'Oznaczenie wydziału prowadzącego księgę wieczystą',
            'Data zapisania księgi wieczystej',
            'Położenie',
            'Właściciel / użytkownik wieczysty / uprawniony',
        ]

        for col in columns:
            try:
                extracted_metadata[col] = re.search(col + r'\s*\n([^\n]+)', metadata).group(1).strip()
            except Exception as e:
                logger.warning(f"Failed to extract info for column '{col}'. Error: {e}")
                extracted_metadata[col] = ""
        return extracted_metadata
    
    def get_sections_content(self) -> Dict[str, str]:
        """Retrieve content from different sections within the book.

        Returns:
            Dict[str, str]: sections content information.
        """
        sections_content = {}
        sections = ['Dział I-O', 'Dział I-Sp', 'Dział II', 'Dział III', 'Dział IV']

        for section in sections:
            try:
                self.driver.find_element(By.CSS_SELECTOR, f'input[type="submit"][value="{section}"]').click()
                sections_content[section] = element_exp("contentDzialu", self.driver).text
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Failed to get department content for {section}. Error: {e}")
                sections_content[section] = ""
        return sections_content
    
    def get_book_content(self) -> Dict[str, str]:
        """Fetch complete book content, including metadata and department information.

        Returns:
            Dict[str, str]: Combined book content information.
        """
        try:
            if self.driver.find_element(By.XPATH, "//*[contains(text(), 'Wynik wyszukiwania księgi wieczystej')]"):
                metadata = element_exp('content-wrapper', self.driver).text
                metadata_dict = self.get_land_register_info_from_metadata(metadata)

                element_exp('przyciskWydrukZwykly', self.driver).click()

                sections_content_dict = self.get_sections_content()
                metadata_dict.update(sections_content_dict)
                return metadata_dict
        except NoSuchElementException:
            logger.warning("Failed to find the book search results. Error: {e}")
        return {}

    def enter_identification_details(self, identification: Dict[str, str]) -> bool:
        """Enter the identification details into the web form.

        Args:
            identification (Dict[str, str]): The identification details.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            for element, key in identification.items():
                element_exp(element, self.driver).send_keys(key)
            element_exp('wyszukaj', self.driver).click()
            time.sleep(0.5)
            return True
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            logger.error(f"Error entering identification details: {e}")
            time.sleep(self.sleep)
            self.driver.get(self.url)
            self.driver.refresh()
            return False

    def is_control_number_incorrect(self, book_code: str) -> bool:
        """Check if the control number is incorrect.

        Args:
            book_code (str): The book code.

        Returns:
            bool: True if the control number is incorrect, False otherwise.
        """
        try:
            if element_exp('cyfraKontrolna--cyfra-kontrolna', self.driver).is_displayed():
                logger.warning(f"Incorrect control number for {book_code}")
                return True
        except NoSuchElementException:
            logger.info(f"Book with identification {book_code} has correct control number.")
        return False

    def is_book_found(self) -> bool:
        """Check if the book is found on the web page.

        Returns:
            bool: True if the book is found, False otherwise.
        """
        try:
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            return 'nie została odnaleziona' not in page_text
        except NoSuchElementException:
            logger.warning("Exception during checking if the book is found.")
            return False

    def run_book_sourcing(self) -> None:
        """Run the book sourcing process to retrieve and print book information."""
        for number in range(int(1e8)):
            id_book = f'{number:08}'
            control_number = str(self.get_control_number(self.department_code, id_book))

            identification = {
                'kodWydzialuInput': self.department_code,
                'numerKsiegiWieczystej': id_book,
                'cyfraKontrolna': control_number,
            }
            book_code = "/".join(identification.values())

            if not self.enter_identification_details(identification):
                db.append_to_failed_books(book_code, "API_EXCEPTION")
                continue

            elif self.is_control_number_incorrect(book_code):
                db.append_to_failed_books(book_code, "INCORRECT_CONTROL_NUMBER")
                continue

            elif self.is_book_found():
                content = self.get_book_content()
                content['id'] = book_code
                db.append_to_books_metadata(content)
                self.driver.get(self.url)
            else:
                logger.warning(f"Book {book_code} has not been found.")
                db.append_to_failed_books(book_code, "NOT_FOUND")
                element_exp('powrotDoKryterii', self.driver).click()


def run_sourcing_for_department(driver: WebDriver, department_queue: queue.Queue, url: str, lock: threading.Lock):
    """Run the book sourcing process for departments in a queue.

    Args:
        driver (webdriver.Chrome): The WebDriver instance to use.
        department_queue (queue.Queue): Queue of departments to process.
        url (str): The URL of the web page to interact with.
        lock (threading.Lock): Lock for synchronization.
    """
    while not department_queue.empty():
        try:
            department = department_queue.get_nowait()
        except queue.Empty:
            break

        with lock:
            logger.info(f"Driver {threading.current_thread().name} processing department: {department}")

        try:
            evidence_book = EvidenceBook(driver, department, url)
            evidence_book.run_book_sourcing()
        except Exception as e:
            with lock:
                logger.warning(f"Error processing department {department}: {e}")
        finally:
            department_queue.task_done()

    driver.quit()
    
def parallel_book_sourcing(drivers: List[WebDriver], departments: List[str], url: str) -> None:
    """Run sourcing in parallel across multiple drivers and departments.

    Args:
        drivers (List[WebDriver]): List of WebDriver instances.
        departments (List[str]): List of departments to process.
        url (str): The URL of the web page to interact with.
    """
    department_queue = queue.Queue()
    for department in departments:
        department_queue.put(department)

    lock = threading.Lock()
    threads = []

    for driver in drivers:
        thread = threading.Thread(
            target=run_sourcing_for_department,
            args=(driver, department_queue, url, lock),
            name=f"DriverThread-{drivers.index(driver)}"
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    
if __name__ == "__main__":
    drivers_setup = setup.WebDriverSetup(nr_instances = int(get_config()['NUMBER_OF_PROCESSES']))
    drivers = drivers_setup.get_drivers()
    depatmnet_codes = get_department_codes(drivers[0])
    
    parallel_book_sourcing(drivers, depatmnet_codes, drivers_setup._get_url())
