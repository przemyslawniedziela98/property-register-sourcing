import unittest
from unittest.mock import patch, MagicMock
from selenium.webdriver.chrome.webdriver import WebDriver
from setup import WebDriverSetup  

class TestSetup(unittest.TestCase):
    def setUp(self):
        """Prepare resources for each test."""
        self.headless = True
        self.nr_instances = 2
        self.setup = WebDriverSetup(headless=self.headless, 
                                    nr_instances=self.nr_instances)
        self.url = self.setup._get_url()

    @patch('setup.webdriver.Chrome')
    def test_create_driver(self, mock_chrome):
        """Test if create_driver method creates a Chrome driver correctly."""
        mock_chrome.return_value = MagicMock(spec=WebDriver)
        driver = self.setup.create_driver()
        self.assertIsInstance(driver, WebDriver)

    @patch('setup.configparser.ConfigParser')
    def test_get_url(self, mock_config):
        """Test retrieval of URL from configuration file."""
        mock_parser = MagicMock()
        mock_parser.read.return_value = True
        mock_parser.__getitem__.return_value = {'URL': '"' + self.url + '"'}
        mock_config.return_value = mock_parser
        url = self.setup._get_url()
        self.assertEqual(url, self.url)

    @patch('setup.webdriver.Chrome')
    @patch('setup.WebDriverSetup._get_url', 
           return_value='https://przegladarka-ekw.ms.gov.pl/eukw_prz/KsiegiWieczyste/wyszukiwanieKW')
    def test_single_driver_setup(self, mock_get_url, mock_chrome):
        """Test if single_driver_setup initializes a driver and handles the initial setup."""
        mock_driver = MagicMock(spec=WebDriver)
        mock_chrome.return_value = mock_driver
        driver = self.setup.single_driver_setup()
        mock_driver.get.assert_called_once_with(self.url)
        self.assertEqual(driver, mock_driver)

    @patch('setup.WebDriverSetup.single_driver_setup')
    def test_get_drivers(self, mock_single_driver_setup):
        """Test if get_drivers creates the correct number of driver instances."""
        mock_single_driver_setup.return_value = MagicMock(spec=WebDriver)
        drivers = self.setup.get_drivers()
        self.assertEqual(len(drivers), self.nr_instances)
        self.assertTrue(all(isinstance(driver, WebDriver) for driver in drivers))

if __name__ == '__main__':
    unittest.main()


