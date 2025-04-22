"""
truncate_append.py

This script provides a function to truncate and append data to a feature service or hosted table in Esri Portal.
It handles the following tasks:
1. Creates a temporary File Geodatabase (FGDB) to store exported data.
2. Zips the FGDB and uploads it to Esri Portal.
3. Truncates the target feature service or table, either by deleting features in batches or using the truncate operation.
4. Appends new data from the uploaded FGDB to the target feature service or table.
5. Cleans up temporary files and uploaded items after processing.

Dependencies:
- `arcpy` for geoprocessing tasks.
- `arcgis` for interacting with Esri Portal.
- `os`, `time`, `uuid`, and `zipfile` for file and system operations.

Functions:
- `truncate_append(local_object, item_id, layer_index, feature_service, disable_sync, gis, oid)`:
  Main function to perform the truncate and append operation.

Usage:
Call the `truncate_append` function with the required parameters to update a feature service or table in Esri Portal.
"""

import os
import time
import uuid
from zipfile import ZipFile

import arcgis.features
import arcpy


def truncate_append(local_object, item_id, layer_index, feature_service, disable_sync, gis, oid):
    arcpy.env.overwriteOutput = True
    # Start Timer
    start_time = time.time()

    # Create UUID variable for GDB
    gdb_id = str(uuid.uuid1())

    # Function to Zip FGD
    def zip_dir(dir_path, zip_path):
        """Zip File Geodatabase"""
        zipf = ZipFile(zip_path, mode='w')
        gdb_zip = os.path.basename(dir_path)
        for root, _, files in os.walk(dir_path):
            for file in files:
                if 'lock' not in file:
                    file_path = os.path.join(root, file)
                    zipf.write(str(file_path), str(os.path.join(gdb_zip, file)))
        zipf.close()

    print("Creating temporary File Geodatabase")
    gdb = arcpy.CreateFileGDB_management(arcpy.env.scratchFolder, gdb_id)[0]

    # Export featureService classes to temporary File Geodatabase
    fc_name = os.path.basename(local_object)
    fc_name = fc_name.split('.')[-1]
    print(f"Exporting {fc_name} to temp FGD")
    if feature_service:
        arcpy.conversion.FeatureClassToFeatureClass(local_object, gdb, fc_name)
    else:
        arcpy.conversion.TableToTable(local_object, gdb, fc_name)

    # Zip temp FGD
    print("Zipping temp FGD")
    zip_dir(gdb, gdb + ".zip")

    # Upload zipped File Geodatabase
    print("Uploading File Geodatabase")
    fgd_properties = {'title': gdb_id, 'tags': 'temp file geodatabase', 'type': 'File Geodatabase'}
    fgd_item = gis.content.add(item_properties=fgd_properties, data=gdb + ".zip")

    # Get featureService/hostedTable layer
    service_layer = gis.content.get(item_id)
    if feature_service:
        f_lyr = service_layer.layers[layer_index]
    else:
        f_lyr = service_layer.tables[layer_index]

    # Truncate Feature Service
    # If views exist, or disableSync = False use delete_features.  OBJECTIDs will not reset
    flc = arcgis.features.FeatureLayerCollection(service_layer.url, gis)
    has_views = False
    try:
        if flc.properties.hasViews:
            print("Feature Service has view(s)")
            has_views = True
    except:
        has_views = False

    if has_views or disable_sync:
        # Get Min OBJECTID
        min_oid = f_lyr.query(
            out_statistics=[
                {"statisticType": "MIN", "onStatisticField": oid, "outStatisticFieldName": "MINOID"}])
        min_objectid = min_oid.features[0].attributes['MINOID']

        # Get Max OBJECTID
        max_oid = f_lyr.query(
            out_statistics=[
                {"statisticType": "MAX", "onStatisticField": oid, "outStatisticFieldName": "MAXOID"}])
        max_objectid = max_oid.features[0].attributes['MAXOID']

        # If more than 2,000 features, delete in 2000 increments
        print("Deleting features")
        if max_objectid and min_objectid:
            if (max_objectid - min_objectid) > 2000:
                x = min_objectid
                y = x + 1999
                while x < max_objectid:
                    query = f"{oid} >= {x} AND {oid} <= {y}"
                    f_lyr.delete_features(where=query)
                    x += 2000
                    y += 2000
            # Else if less than 2,000 features, delete all
            else:
                print("Deleting features")
                f_lyr.delete_features(where="1=1")

    # If no views and disableSync is True: disable Sync, truncate, and then re-enable Sync.  OBJECTIDs will reset
    elif has_views is False and disable_sync:
        if flc.properties.syncEnabled:
            print("Disabling Sync")
            properties = flc.properties.capabilities
            update_dict = {"capabilities": "Query", "syncEnabled": False}
            flc.manager.update_definition(update_dict)

            print("Truncating Feature Service")
            f_lyr.manager.truncate()

            print("Enabling Sync")
            update_dict = {"capabilities": properties, "syncEnabled": True}
            flc.manager.update_definition(update_dict)
        else:
            print("Truncating Feature Service")
            f_lyr.manager.truncate()

    # Append features from featureService class/hostedTable
    print("Appending features")

    f_lyr.append(item_id=fgd_item.id, upload_format="filegdb", upsert=False, field_mappings=[])

    # Delete Uploaded File Geodatabase
    print("Deleting uploaded File Geodatabase")

    for _ in range(10):
        try:
            fgd_item.delete()
            break
        except:
           print('---DELETE GDB ITEM FAIL---')

    # Delete temporary File Geodatabase and zip file
    print("Deleting temporary FGD and zip file")
    arcpy.Delete_management(gdb)
    os.remove(gdb + ".zip")

    end_time = time.time()
    elapsed_time = round((end_time - start_time) / 60, 2)
    print("Script finished in {0} minutes".format(elapsed_time))
