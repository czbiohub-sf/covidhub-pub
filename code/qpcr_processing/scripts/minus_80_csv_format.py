import csv

# make sure to reset these variables before any script rerun
# they are there to indicate the variable format
date_time = "5/11/2020 13:03:00"
researcher_name = "Vida Ahyong"
sample_type = "Original Sample"
input_file_name = "VAfrozenmay10.csv"

freezer = "clia-storage80-1"
output_file_name = input_file_name.replace(".csv", "") + "_new_format.csv"

reader = csv.reader(open(input_file_name))
writer = csv.writer(open(output_file_name, mode="w"))

# write header
writer.writerow(
    [
        "date",
        "institution",
        "researcher name",
        "sample_plate_barcode",
        "sample type",
        "freezer",
        "shelf",
        "rack",
        "volume",
        "notes",
        "top_a",
        "bottom_b",
    ]
)

# reformat rows to be easily c/p'd into https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit#gid=1804090556
for row in reader:
    sample_plate_barcode = row[0]
    shelf = row[1]
    rack = row[2]

    # original file has a Location variable #Shelf (e.g. 1A) that combines the block and the front/back location
    top_a, bottom_b = "", ""
    if row[3][1] == "A":
        top_a = "Block " + row[3][0]
    elif row[3][1] == "B":
        bottom_b = "Block " + row[3][0]

    if top_a == "Block 7":
        top_a += " [back]"
    elif bottom_b == "Block 7":
        bottom_b += " [back]"
    elif top_a == "Block 1":
        top_a += " [front]"
    elif bottom_b == "Block 1":
        bottom_b += " [front]"

    writer.writerow(
        [
            date_time,
            "",
            researcher_name,
            sample_plate_barcode,
            sample_type,
            freezer,
            shelf,
            rack,
            "",
            "",
            top_a,
            bottom_b,
        ]
    )
