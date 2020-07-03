# flake8: noqa

import pandas as pd
from lib.google import drive


def color_other_plates_in_batch_used(val):
    """
    Takes a scalar and returns a string with
    the css property `'color: red'` if strings in target list, black otherwise.
    """
    color = (
        "red"
        if val in sum(batch_plates_previously_used[barcode_cols].values.tolist(), [])
        else "black"
    )
    return "color: %s" % color


def qpcr_run_debugging(args):
    """the goal of this function is to generate a diagnostic excel file for a failed run"""

    cfg = Config()
    google_credentials = gutils.get_secrets_manager_credentials(args.secret_id)

    drive_service = drive.get_service(google_credentials)

    database_folder_id = drive.get_folder_id_of_path(drive_service, ["Covid19"])
    with drive.get_file_by_name(
        drive_service, database_folder_id, "Covid-19 Collective Form (Responses)"
    ) as fh:
        # Load the plate reagent list
        reagent_inventory = pd.read_excel(fh, sheet_name="Reagent Tracking")
        # Load the BRAVO runs info
        bravo_runs = pd.read_excel(fh, sheet_name="Bravo RNA extractions")

    # Barcode in the form turns into the file name.
    # This is written in main spreadsheet's worksheet `Failed_PCR_run` under column `Failed qPCR Plate Barcode`

    problematicbarcode = args.plate_barcode

    if problematicbarcode == None:
        failed_runs = pd.read_excel(fh, sheet_name="Failed_PCR_run")
        problematicbarcode = failed_runs.iloc[-1]["Failed qPCR Plate Barcode"]
    filename = f"ReagentDebuggingPlate{problematicbarcode}.xlsx"

    # Find problematic run
    run = bravo_runs[bravo_runs["384 PCR Plate barcode"] == problematicbarcode]

    barcode_cols = [b for b in run.columns if "arcode" in b]
    barcode_cols = [b for b in barcode_cols if "96" not in b]

    reagent_used = pd.DataFrame(
        index=barcode_cols, columns=["barcode_of_this_run"]
    )  # +list(reagent_inventory.columns))
    reagent_used["barcode_of_this_run"] = list(list(run[barcode_cols].values)[0])

    # Get the reagent plates prepared as a batch
    reagent_batches = pd.DataFrame()
    for i in reagent_used.index:
        q = reagent_used.loc[i, "barcode_of_this_run"]
        raux = reagent_inventory.loc[
            reagent_inventory[reagent_inventory.isin([q])].dropna(thresh=1).index
        ]
        raux["barcode_of_this_run"] = q
        raux["reagent_type_associated_with_barcode_for_this_run"] = i
        reagent_batches = pd.concat([reagent_batches, raux], axis=0)

    reagent_batches_grouped = (
        reagent_batches.groupby(
            ["reagent_type_associated_with_barcode_for_this_run", "barcode_of_this_run"]
        )[
            "reagent_type_associated_with_barcode_for_this_run",
            "What reagent plate are you preparing?",
        ]
        .agg({"count": len, "set": set})
        .reset_index()
    )

    reagent_batches_grouped.columns = [
        "".join(col) for col in reagent_batches_grouped.columns
    ]

    reagent_batches_grouped = reagent_batches_grouped.rename(
        columns={
            "countWhat reagent plate are you preparing?": "how many batches associated with barcode for this run",
            "setWhat reagent plate are you preparing?": "to what type of reagent plate do they match?",
        }
    )

    reagent_batches = reagent_batches.reset_index()
    batch_barcode_cols = [
        b for b in reagent_batches.columns if "Reagent Plate Barcode" in b
    ]
    reagent_batches_barcodes = reagent_batches[batch_barcode_cols]
    bravo_runs_except_run = bravo_runs.drop(run.index, axis=0)

    all_barcodes = sum(reagent_batches_barcodes.values.tolist(), [])
    all_barcodes = [x for x in all_barcodes if str(x) != "nan"]

    batch_plates_previously_used = bravo_runs_except_run.loc[
        bravo_runs_except_run[bravo_runs_except_run.isin(all_barcodes)]
        .dropna(thresh=1)
        .index
    ]

    batch_plates_previously_used = batch_plates_previously_used.reset_index()

    writer = pd.ExcelWriter(filename, engine="openpyxl")  # xlsxwriter
    run.to_excel(writer, sheet_name="problematic_run")
    reagent_used.to_excel(writer, sheet_name="reagent_plates_used")
    reagent_batches_grouped.to_excel(writer, sheet_name="reagent_plates_type")
    reagent_batches.to_excel(writer, sheet_name="reagents_same_batch")
    reagent_batches.style.applymap(color_other_plates_in_batch_used).to_excel(
        writer, sheet_name="other_plates_in_batch_used"
    )
    batch_plates_previously_used.to_excel(
        writer, sheet_name="run_info_plates_previously_used"
    )
    writer.save()

    # Upload to Google Drive
    write_folder_id = drive.get_folder_id_of_path(
        drive_service, ["Covid19", "Debugging"],
    )
    with open(filename, "r") as in_fh, drive.put_file(
        drive_service, write_folder_id, filename
    ) as out_fh:
        out_fh.write(in_fh.read())


def main():
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--plate_barcode", required=True)
    parser.add_argument("--secret-id", default="covid-19/google_creds")

    args = parser.parse_args()

    qpcr_run_debugging(args)


if __name__ == "__main__":
    main()
