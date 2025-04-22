"""
File: main.py
Description: This script automates the process of downloading, processing, and updating
             the ACF Head Start Locations feature class in Esri Portal. It performs
             the following tasks:

             1. Downloads the latest ACF data from a configured URL.
             2. Converts the downloaded data into a CSV file.
             3. Creates a point feature class from the CSV using latitude and longitude fields.
             4. Formats specific fields with zero-padded values.
             5. Updates the Esri Portal feature service by truncating and appending the new data.
             6. Logs all activities and errors for debugging and auditing purposes.

Dependencies:
- `arcpy` for geoprocessing tasks.
- `arcgis` for interacting with Esri Portal.
- `requests` for HTTP requests.
- `pandas` for data manipulation.
- `keyring` for securely accessing Esri Portal credentials.
- `json`, `os`, `sys`, `datetime`, and `logging` for various system operations.

Functions:
- `open_json(json_config_file)`: Reads and returns the contents of a JSON configuration file.
- `download_acf_data()`: Downloads the ACF data from the configured URL.
- `write_to_csv(data_in)`: Writes the downloaded data to a CSV file after processing.
- `zfill_strings()`: Formats specific fields in the feature class with zero-padded values.

Usage:
Run the script as a standalone program. Ensure the required configuration file and dependencies
are in place. The script logs its activities to `main.log` in the `logs` directory.

Error Handling:
The script includes error handling for HTTP requests, file operations, and geoprocessing tasks.
Errors are logged, and an email notification is sent if an error occurs.
"""
import datetime
import io
import json
import logging
import os
import sys

import arcpy
import keyring as kr
import pandas as pd
import requests
from arcgis.gis import GIS
from requests.exceptions import ChunkedEncodingError

from truncate_append import truncate_append

log = rf"logs\main.log"
logging.basicConfig(
    filename=log,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

acf_feature_class = "ACF_Head_Start_Locations"


def load_json_config(json_config_file):
    """Open and return the contents of a JSON configuration file.

    Args:
        json_config_file (str): The path to the JSON configuration file.

    Returns:
        dict: The contents of the JSON file as a dictionary.
    """
    try:
        with open(json_config_file, "r") as configFile:
            jsn_config = json.load(configFile)
        return jsn_config
    except FileNotFoundError as e:
        logging.error(f"Configuration file not found: {e}")
        sys.exit()
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON format: {e}")
        sys.exit()


def get_acf_head_start_data():
    """Retrieve ACF Head Start data from the configured URL.

    This function sends an HTTP GET request to the URL specified in the JSON configuration file
    and retrieves the content of the response. If the request fails due to a `ChunkedEncodingError`,
    the error is logged, and the script exits.

    Returns:
        bytes: The content of the downloaded data.

    Raises:
        ChunkedEncodingError: If there is an issue with the HTTP request.
    """
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/118.0", }
    try:
        response_content = requests.get(json_config["acf_url"], headers=headers).content
        return response_content
    except ChunkedEncodingError as ex:
        logging.error(ex, exc_info=True)
        sys.exit()


def write_to_csv(data_in):
    """
    Writes the downloaded ACF data to a CSV file after processing.

    This function processes the input data, renames specific columns, and saves the result
    as a CSV file. It ensures that the data is properly formatted for further use.

    Args:
        data_in (bytes): The raw data downloaded from the ACF URL in byte format.

    Raises:
        Exception: If there is an error during data processing or file writing, it logs the error
                   and exits the script.
    """
    try:
        df = pd.read_csv(io.StringIO(data_in.decode("utf-8")))
        df = df.drop(df.columns[[0]], axis=1)
        df = df.rename(
            columns={
                "zip": "zip_int",
                "zip_4": "zip_4_int",
                "program_admin_zip": "program_admin_zip_int",
                "program_admin_zip_4": "program_admin_zip_4_int",
                "program_admin_ID": "program_admin_ID_int",
            }
        )
        df.to_csv(csv_file_path)
    except Exception as e:
        logging.error(f"Error writing to CSV: {e}", exc_info=True)
        sys.exit()


def format_fields_with_zero_padding():
    def calculate_field_zfill(in_table, field, field_expression, zfill_len):
        """Calculate a field value with zero-fill padding in an ArcGIS table.

        Args:
            in_table (str): The path to the input table.
            field (str): The name of the field to calculate.
            field_expression (str): The field expression to evaluate.
            zfill_len (int): The length to zero-fill the field value to.
        """
        arcpy.management.CalculateField(
            in_table=in_table,
            field=field,
            expression=f"str(!{field_expression}!).zfill({zfill_len})",
            expression_type="PYTHON3",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS",
        )

    try:
        arcpy.AddField_management(acf_feature_class, "zip", "TEXT")
        arcpy.AddField_management(acf_feature_class, "zip_4", "TEXT")
        arcpy.AddField_management(acf_feature_class, "program_admin_zip", "TEXT")
        arcpy.AddField_management(acf_feature_class, "program_admin_zip_4", "TEXT")
        arcpy.AddField_management(acf_feature_class, "program_admin_ID", "TEXT")

        calculate_field_zfill(acf_feature_class, "zip", "zip_int", 5)
        calculate_field_zfill(acf_feature_class, "zip_4", "zip_4_int", 4)
        calculate_field_zfill(acf_feature_class, "program_admin_zip", "program_admin_zip_int", 5)
        calculate_field_zfill(acf_feature_class, "program_admin_zip_4", "program_admin_zip_4_int", 4)
        calculate_field_zfill(acf_feature_class, "program_admin_ID", "program_admin_ID_int", 3)

        arcpy.DeleteField_management(
            acf_feature_class,
            [
                "zip_int",
                "zip_4_int",
                "program_admin_zip_int",
                "program_admin_zip_4_int",
                "program_admin_ID_int",
            ],
        )
    except arcpy.ExecuteError as e:
        logging.error(f"ArcPy error: {e}", exc_info=True)
        sys.exit()
    except Exception as e:
        logging.error(f"Unexpected error in zfill_strings: {e}", exc_info=True)
        sys.exit()



if __name__ == "__main__":
    try:
        start = datetime.datetime.now()

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = geodatabase_path = r"YOUR_PATH\ACF_Head_Start.gdb"

        json_config = load_json_config(r"config\acf_head_start.json")

        today = datetime.date.today()
        current_date_str = today.strftime("%Y%m%d")
        csv_file_path = rf"{current_date_str}_ACF_Head_Start.csv"

        response_in_memory = get_acf_head_start_data()

        write_to_csv(response_in_memory)

        arcpy.management.XYTableToPoint(csv_file_path, acf_feature_class, "longitude", "latitude")

        format_fields_with_zero_padding()

        gis = GIS("URL", "USERNAME", kr.get_password("URL", "USERNAME"))

        truncate_append(acf_feature_class, json_config["esri_portal"]["item_id"], 0, True, True, gis, 'OBJECTID')

        os.remove(csv_file_path)

        end = datetime.datetime.now()
        logging.info(f"Total time: {end - start}")
    except Exception as e:
        logging.error(f"Unexpected error in main script: {e}", exc_info=True)
        sys.exit()