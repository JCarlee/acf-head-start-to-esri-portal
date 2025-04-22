# ACF Update Utility
A Python-based utility to update the ACF Head Start data in a Geodatabase (GDB) using ArcPy and other libraries.

## Author
**John Carlee**

## Overview
This script automates the process of downloading, processing, and updating the ACF Head Start Locations feature class in Esri Portal. It performs the following tasks:
1. Downloads the latest ACF data from a configured URL.
2. Converts the downloaded data into a CSV file.
3. Creates a point feature class from the CSV using latitude and longitude fields.
4. Formats specific fields with zero-padded values.
5. Updates the Esri Portal feature service by truncating and appending the new data.
6. Logs all activities and errors for debugging and auditing purposes.

## Dependencies
* [Python 3](https://www.python.org/)
* [ArcPy](https://pro.arcgis.com/en/pro-app/arcpy/get-started/what-is-arcpy-.htm)
* [pandas](https://pandas.pydata.org/)
* [requests](https://docs.python-requests.org/en/master/)
* [arcgis](https://developers.arcgis.com/python/)
* [keyring](https://pypi.org/project/keyring/)

## Workflow
1. **Download the newest data from ACF**  
   The script downloads the latest data from the configured URL and saves it with the current date (YYYYMMDD) in the filename.
2. **Save with YYYYMMDD in filename**  
   The downloaded CSV file is saved in the `Downloads` directory with the date appended to the filename.
3. **Convert to table within GDB**  
   The CSV file is converted to a table within the Geodatabase (GDB).
4. **Convert table to feature class using latitude and longitude fields**  
   The table is then converted to a feature class using the latitude and longitude fields.
5. **Format fields with zero-padded values**  
   Specific fields are formatted with zero-padded values for consistency.
6. **Update Esri Portal feature service**  
   The new feature class replaces the existing production feature class in Esri Portal.
7. **Remove temporary files**  
   The script deletes the temporary CSV file after processing.

## Script Details

### `main.py`
This script performs the following functions:

#### `load_json_config(json_config_file)`
* Loads and returns the contents of a JSON configuration file.

#### `get_acf_head_start_data()`
* Downloads the newest data from the ACF website.

#### `write_to_csv(data_in)`
* Writes the downloaded data to a CSV file after processing.

#### `format_fields_with_zero_padding()`
* Formats specific fields in the feature class with zero-padded values.

#### `truncate_append()`
* Updates the Esri Portal feature service by truncating and appending the new data.

## Logging
* The script logs its activities to `main.log` located in the `logs` directory. This includes information about the start and end times, as well as any errors encountered during execution.

## Error Handling
* The script includes error handling for HTTP requests, file operations, and geoprocessing tasks. Errors are logged, and the script exits gracefully if an error occurs.

## Usage
To run the script, execute the following command in your terminal:
```sh
python main.py