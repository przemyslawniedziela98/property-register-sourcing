import unittest
from unittest.mock import patch, MagicMock, create_autospec
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from evidence_books_sourcing import (
    EvidenceBook,
    get_config,
    get_department_codes,
)

class TestEvidenceBook(unittest.TestCase):
    def setUp(self):
        self.mock_driver = create_autospec(WebDriver)
        self.mock_driver.find_element.return_value = MagicMock(spec=WebElement)
        self.url = "https://przegladarka-ekw.ms.gov.pl/eukw_prz/KsiegiWieczyste/wyszukiwanieKW"
        self.department_code = "KI1I"
        self.evidence_book = EvidenceBook(self.mock_driver, self.department_code, self.url)

    @patch('evidence_books_sourcing.element_exp')
    def test_get_control_number(self, mock_element_exp):
        """Test control number calculation """
        control_number = self.evidence_book.get_control_number(self.department_code, "00000008")
        self.assertEqual(control_number, 0, "Control number should be calculated as 0")

    @patch('evidence_books_sourcing.element_exp')
    def test_get_land_register_info_from_metadata(self, mock_element_exp):
        """Test extraction of metadata from a string """
        metadata = (
            "Numer księgi wieczystej\nAB1C\n"
            "Typ księgi wieczystej\nGRUNTOWA\n"
            "Oznaczenie wydziału prowadzącego księgę wieczystą\nWarszawa\n"
            "Data zapisania księgi wieczystej\n2024-08-02\n"
            "Położenie\nSiewna\n"
            "Właściciel / użytkownik wieczysty / uprawniony\nJan Kowalski\n"
        )
        extracted_metadata = self.evidence_book.get_land_register_info_from_metadata(metadata)
        expected_metadata = {
            'Numer księgi wieczystej': 'AB1C',
            'Typ księgi wieczystej': 'GRUNTOWA',
            'Oznaczenie wydziału prowadzącego księgę wieczystą': 'Warszawa',
            'Data zapisania księgi wieczystej': '2024-08-02',
            'Położenie': 'Siewna',
            'Właściciel / użytkownik wieczysty / uprawniony': 'Jan Kowalski',
        }
        self.assertEqual(extracted_metadata, expected_metadata, "Metadata extraction failed")

    @patch('evidence_books_sourcing.element_exp')
    def test_enter_identification_details(self, mock_element_exp):
        """Test entering identification details """
        identification = {
            'kodWydzialuInput': self.department_code,
            'numerKsiegiWieczystej': '00000001',
            'cyfraKontrolna': '6',
        }
        mock_element = MagicMock()
        mock_element_exp.return_value = mock_element

        success = self.evidence_book.enter_identification_details(identification)
        self.assertTrue(success, "Identification details should be entered successfully")
        mock_element_exp.assert_any_call('kodWydzialuInput', self.mock_driver)
        mock_element_exp.assert_any_call('numerKsiegiWieczystej', self.mock_driver)
        mock_element_exp.assert_any_call('cyfraKontrolna', self.mock_driver)
        mock_element_exp.assert_any_call('wyszukaj', self.mock_driver)

    def test_get_config(self):
        """Test retrieving configuration settings """
        with patch('evidence_books_sourcing.configparser.ConfigParser.read', return_value=True):
            with patch('evidence_books_sourcing.configparser.ConfigParser.__getitem__', return_value={'ERROR_SLEEP': '300'}):
                config = get_config()
                self.assertIn('ERROR_SLEEP', config, "Config should have 'ERROR_SLEEP'")
                self.assertEqual(config['ERROR_SLEEP'], '300', "Config 'ERROR_SLEEP' should be '300'")

    @patch('evidence_books_sourcing.WebDriverWait')
    @patch('evidence_books_sourcing.element_exp')
    def test_get_department_codes(self, mock_element_exp, mock_webdriver_wait):
        """Test fetching department codes from a dropdown """
        mock_dropdown_element = MagicMock()
        mock_dropdown_element.text = "\nAA1B - Miasto 1\nBB2C - Miasto 2\n"
        mock_webdriver_wait.return_value.until.return_value = mock_dropdown_element

        codes = get_department_codes(self.mock_driver)
        expected_codes = ['AA1B', 'BB2C']
        self.assertEqual(codes, expected_codes, "Department codes should be extracted correctly")


if __name__ == "__main__":
    unittest.main()
