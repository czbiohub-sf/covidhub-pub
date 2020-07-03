import csv

from comet.lib.bind_index_plate import bind_index_plate


def test_bind_index(
    tmp_path,
    input_index_map,
    input_384_plate_map,
    expected_nov_seq_output,
    expected_next_seq_output,
):
    next_seq_output, nov_seq_output = bind_index_plate(
        plate=input_384_plate_map,
        index_map=input_index_map,
        tracking_name="384_SEQ007_DBP-10",
        run_path=tmp_path,
    )
    verify_csvs_match(nov_seq_output, expected_nov_seq_output)
    verify_csvs_match(next_seq_output, expected_next_seq_output)


def verify_csvs_match(output_csv, expected_data):
    with (output_csv).open("r") as t1:
        rdr1 = csv.reader(t1)
        rdr2 = csv.reader(expected_data)
        for row1, row2 in zip(rdr1, rdr2):
            assert row1 == row2
