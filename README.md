# Property Register Sourcing

This Property Register Sourcing project leverages Selenium WebDriver to automate interaction with the [Electronic Land and Mortgage Register](https://przegladarka-ekw.ms.gov.pl/eukw_prz/KsiegiWieczyste/wyszukiwanieKW?komunikaty=true&kontakt=true&okienkoSerwisowe=false) from Polish Ministry of Justice. 
It extracts department codes, retrieves evidence book metadata from all sections and stores the data in a MongoDB database. 
The system supports parallel processing to handle multiple departments simultaneously.


## Project Modules

### `setup`

Configures logging and initializes Selenium WebDriver instances. Manages logging setup and WebDriver creation.

### `evidence book sourcing`

Core module for interacting with the  Property Register system. Handles department code retrieval, control number calculation, metadata extraction, content fetching from different sections of the book and error handling during the sourcing process.

### `database`

Manages MongoDB interactions for storing book metadata and failed sourcing attempts. 

## Additional Components

- **Tests**: Includes unit tests for the `setup` and `evidence book sourcing` modules to ensure functionality.
- **`run_sourcing.sh`**: A shell script to automate the execution of the book sourcing process.
- **`config.ini`**: Configuration file for setting the URL, number of WebDriver instances and error sleep duration.
- **`requirements.txt`**: Lists the Python packages required for the project.

