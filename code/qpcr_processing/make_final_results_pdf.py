import html
import math
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Mapping, Sequence

from pkg_resources import resource_filename
from reportlab.graphics.barcode.code128 import Code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

from covidhub.config import get_git_info
from covidhub.constants import Call, COLS_96, ROWS_96
from qpcr_processing.ct_curves import plot_background_ct_curves, plot_ct_curves
from qpcr_processing.processing_results import ProcessingResults


class _PDF:
    # color code for reporting calls for genes (first three)
    # as well as for the overall control result (last two)
    RESULTS_COLOR_CODE = {
        Call.INV: colors.blue,
        Call.IND: colors.orange,
        Call.POS: colors.red,
        Call.POS_REVIEW: colors.red,
        Call.POS_CLUSTER: colors.red,
        Call.POS_HOTWELL: colors.red,
    }

    CONTROLS_COLOR_CODE = {
        "Passed": colors.green,
        "Failed": colors.red,
    }

    # load all the images and make Image objects
    RESOURCES = Path(resource_filename("qpcr_processing", "pdf_resources"))

    CZB_LOGO = Image(RESOURCES / "Biohub_Roundel_only.jpg")
    CZB_LOGO.drawHeight = 0.5 * inch
    CZB_LOGO.drawWidth = 0.5 * inch

    CZI_LOGO = Image(RESOURCES / "czi.jpg")
    CZI_LOGO.drawHeight = 0.5 * inch
    CZI_LOGO.drawWidth = 0.5 * inch

    UCSF_LOGO = Image(RESOURCES / "UCSF_logo_black_RGB.jpg")
    UCSF_LOGO.drawHeight = 0.35 * inch
    UCSF_LOGO.drawWidth = 0.75 * inch

    CA_LOGO = Image(RESOURCES / "ca.jpg")
    CA_LOGO.drawHeight = 0.5 * inch
    CA_LOGO.drawWidth = 0.5 * inch

    MARGIN = 0.25 * inch

    BARCODE_HEIGHT = 0.35 * inch
    BARCODE_WIDTH = 0.01 * inch  # the width of the skinniest individual bar

    HEADER_ROW_HEIGHT = 0.5 * inch
    ACCESSION_ROW_HEIGHT = 3.5 * BARCODE_HEIGHT  # to give space around the barcode
    CONTROL_ROW_HEIGHT = 0.4 * inch  # shorter rows for non-accessioned wells
    EMPTY_ROW_HEIGHT = 0.4 * inch


def make_chain_fn(*functions):
    def chain_fn(canvas: Canvas, doc: BaseDocTemplate):
        for function in functions:
            function(canvas, doc)

    return chain_fn


def make_watermark_fn(
    text: str, paragraph_style: ParagraphStyle,
):
    def watermark_fn(canvas: Canvas, doc: BaseDocTemplate):
        width, height = canvas._pagesize
        canvas.saveState()
        canvas.translate(width / 2, height / 2)
        canvas.rotate(45)
        canvas.setFont(paragraph_style.fontName, paragraph_style.fontSize)
        canvas.setFillColor(paragraph_style.textColor)
        alpha = getattr(paragraph_style, "alpha", 1.0)
        canvas.setFillAlpha(alpha)
        canvas.drawCentredString(0, 0, text)
        canvas.restoreState()

    return watermark_fn


def make_header_fn(
    text: str, paragraph_style: ParagraphStyle, margin=0.15 * inch,
):
    def header_fn(canvas, doc: BaseDocTemplate):
        width, height = canvas._pagesize
        # don't add header to first page or landscape pages
        if canvas._pageNumber == 1 or width > height:
            return
        paragraph = Paragraph(text, paragraph_style)
        paragraph.wrap(width - (2 * margin), height - (2 * margin))
        paragraph.drawOn(canvas, margin, height - (2 * margin))

    return header_fn


def make_footer_fn(
    text: str, paragraph_style: ParagraphStyle, margin=0.1 * inch,
):
    def footer_fn(canvas, doc: BaseDocTemplate):
        width, height = canvas._pagesize
        paragraph = Paragraph(text, paragraph_style)
        paragraph.wrap(width - (2 * margin), height - (2 * margin))
        paragraph.drawOn(canvas, margin, margin)

    return footer_fn


def create_final_pdf(results: ProcessingResults, output_file_handle):
    styles = getSampleStyleSheet()
    doc = BaseDocTemplate(
        output_file_handle,
        pagesize=letter,
        rightMargin=_PDF.MARGIN,
        leftMargin=_PDF.MARGIN,
        topMargin=2 * _PDF.MARGIN,
        bottomMargin=_PDF.MARGIN,
    )

    portrait_frame = Frame(
        _PDF.MARGIN, _PDF.MARGIN, doc.width, doc.height, id="portrait_frame"
    )
    landscape_frame = Frame(0, 0, letter[1], letter[0], id="landscape_frame")

    header_style = ParagraphStyle(
        "header", parent=styles["BodyText"], fontSize=16, alignment=TA_CENTER
    )
    header_text = results.combined_barcode

    watermark_style = ParagraphStyle(
        "footer",
        parent=styles["Heading1"],
        textColor=colors.pink,
        fontSize=36,
        alpha=0.5,
    )

    footer_style = ParagraphStyle(
        "footer", parent=styles["BodyText"], textColor=colors.white
    )
    footer_text = f"Processed by {get_git_info()}"

    page_template_args = [
        make_header_fn(header_text, header_style),
        make_footer_fn(footer_text, footer_style),
    ]
    if results.experimental_run:
        page_template_args.append(
            make_watermark_fn("EXPERIMENTAL! DO NOT REPORT!", watermark_style)
        )
    elif results.invalid_accessions():
        page_template_args.append(
            make_watermark_fn("INVALID ACCESSIONS! DO NOT REPORT!", watermark_style)
        )

    doc.addPageTemplates(
        [
            PageTemplate(
                id="portrait",
                frames=portrait_frame,
                onPageEnd=make_chain_fn(*page_template_args),
            ),
            PageTemplate(
                id="landscape",
                frames=landscape_frame,
                pagesize=landscape(letter),
                onPageEnd=make_chain_fn(*page_template_args),
            ),
        ]
    )

    results_table_style = TableStyle(
        [
            ("SPAN", (0, 0), (1, 0)),  # accession gets two columns
            ("FONT", (0, 0), (-1, 0), styles["Heading1"].fontName),  # bold header
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
    )

    controls_table_style = TableStyle(
        [
            ("FONT", (0, 0), (-1, 0), styles["Heading1"].fontName),  # bold header
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
    )

    results_data = results.protocol.format_header_for_reports(
        start=["Accession", "", "Well", "Call"]
    )

    call_column = results_data[0].index("Call")
    first_ct_column = call_column + 1  # start of cts data

    controls_data = results.protocol.format_header_for_reports(
        start=["Control Type", "Well", "Call"]
    )

    row_heights = [_PDF.HEADER_ROW_HEIGHT]

    notable_wells = defaultdict(list)

    for col in COLS_96:
        for row in ROWS_96:
            well_id = f"{row}{col}"
            well_results = results.get_well_results(well_id)

            gene_cts = [
                well_results.format_ct(gene) or "ND"
                for gene in results.protocol.gene_list
            ]

            row_data = [
                "",
                well_results.accession,
                well_id,
                well_results.call.needs_review,
                *gene_cts,
            ]

            if well_results.control_type is not None:
                row_data[0] = "Control"
                row_heights.append(_PDF.CONTROL_ROW_HEIGHT)

                control_type = well_results.control_type
                control_len = len(controls_data)

                controls_row = [
                    well_results.control_type,
                    well_id,
                    well_results.call,
                    *gene_cts,
                ]
                controls_data.append(controls_row)

                if well_results.call != Call.PASS:
                    controls_table_style.add(
                        "BOX", (0, control_len), (-1, control_len + 1), 1.5, colors.red,
                    )
                    controls_table_style.add(
                        "TEXTCOLOR", (2, control_len), (2, control_len), colors.red,
                    )
                    detailed_status = results.protocol.get_failure_details(control_type)

                    controls_data.append([detailed_status])

                    controls_table_style.add(
                        "SPAN", (0, control_len + 1), (-1, control_len + 1)
                    )
            elif len(well_results.accession) == 0 or well_results.accession == "nan":
                row_data[1] = ""
                row_heights.append(_PDF.EMPTY_ROW_HEIGHT)
            else:
                # a well with a real accession in it
                row_data[0] = Code128(
                    well_results.accession,
                    barHeight=_PDF.BARCODE_HEIGHT,
                    barWidth=_PDF.BARCODE_WIDTH,
                )
                row_heights.append(_PDF.ACCESSION_ROW_HEIGHT)

                if well_results.call.is_positive or well_results.call.rerun:
                    notable_wells[well_results.call].append(
                        f"{well_results.accession} ({well_id})"
                    )

            for j, ct in enumerate(gene_cts):
                if ct == "ND":
                    results_table_style.add(
                        "TEXTCOLOR",
                        (j + first_ct_column, len(results_data)),
                        (j + first_ct_column, len(results_data)),
                        colors.darkgrey,
                    )

            if well_results.call in _PDF.RESULTS_COLOR_CODE:
                results_table_style.add(
                    "TEXTCOLOR",
                    (call_column, len(results_data)),
                    (call_column, len(results_data)),
                    _PDF.RESULTS_COLOR_CODE[well_results.call],
                )

            results_data.append(row_data)

    results_table = Table(
        results_data, rowHeights=row_heights, repeatRows=1, style=results_table_style
    )

    controls_table = Table(
        controls_data, spaceAfter=0.25 * inch, style=controls_table_style
    )

    metadata_table = format_metadata_table(results, styles)

    header_table_style = TableStyle(
        [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "LEFT")]
    )

    logo_table = Table(
        [(_PDF.CZB_LOGO, _PDF.CZI_LOGO), (_PDF.UCSF_LOGO, _PDF.CA_LOGO)],
        colWidths=1 * inch,
    )
    header_table = Table(
        [(logo_table, Paragraph("CLIAHUB - Result Report", styles["Heading1"]))],
        colWidths=[1.75 * inch, 6 * inch],
        style=header_table_style,
    )

    story = [
        header_table,
        metadata_table,
        Paragraph("Controls", styles["Heading1"]),
        controls_table,
        Paragraph("Notes", styles["Heading1"]),
        format_notes(
            results.bravo_metadata.rna_description,
            results.bravo_metadata.qpcr_description,
            results.bravo_metadata.sample_source,
            notable_wells,
            styles,
        ),
        NextPageTemplate("landscape"),  # switching to landscape for next two
        PageBreak(),
        Paragraph(f"{results.combined_barcode} - Plate Map", styles["Title"]),
        create_96_plate_map(results),
        PageBreak(),
        Paragraph(f"{results.combined_barcode} - Ct Curves", styles["Title"]),
        format_ct_curves(results),
        NextPageTemplate("portrait"),  # back to portrait
        PageBreak(),
        Paragraph("Results", styles["Heading1"]),
        results_table,
        PageBreak(),
        Paragraph("Internal Notes", styles["Heading1"]),
        format_internal_notes(results, styles),
        NextPageTemplate("landscape"),  # landscape for background plots
        *format_background_ct_curves(results, styles),
    ]

    # force a 1.4 PDF because that's the minimum to support transparency.
    def canvasmaker(*args, **kwargs):
        return Canvas(*args, pdfVersion=(1, 4), **kwargs)

    doc.build(story, canvasmaker=canvasmaker)


def create_96_plate_map(results: ProcessingResults):
    """Create a 96 well plate map

    Returns
    -------
    `reportlab.platypus.Table`
        platypus table ready for placing in page
    """

    # this is the style for the overall table. Black gridlines,
    # and no padding around the values in the cells
    table_style = TableStyle(
        [
            ("BOX", (1, 1), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (1, 1), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]
    )

    plate_map_dict = defaultdict(dict)

    for i, row in enumerate(ROWS_96):
        for j, col in enumerate(COLS_96):
            well_id = f"{row}{col}"
            well_results = results.get_well_results(well_id)

            ct_results = [
                well_results.format_ct(gene, sig_figs=0) or "ND"
                for gene in results.protocol.gene_list
            ]

            # the style for a mini-table inside a cell.
            # no grid, and a little padding
            cell_style = TableStyle(
                [
                    ("SPAN", (0, 0), (-1, 0)),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )

            for k, ct in enumerate(ct_results):
                if ct == "ND":
                    cell_style.add("TEXTCOLOR", (k, -1), (k, -1), colors.darkgrey)

            if well_results.control_type is not None:
                if well_results.call != Call.PASS:
                    cell_style.add("TEXTCOLOR", (0, 0), (0, 0), colors.coral)

                plate_map_dict[row][col] = Table(
                    [(well_results,), tuple(ct_results)], style=cell_style
                )
                table_style.add(
                    "BACKGROUND", (j + 1, i + 1), (j + 1, i + 1), colors.lightgrey
                )
            elif well_results.accession == "" or well_results.accession == "EMPTY":
                # empty well don't add value info
                plate_map_dict[row][col] = Table(
                    [("",), tuple(ct_results)], style=cell_style
                )
            else:
                cell_style.add("SPAN", (0, 1), (-1, 1))
                cell_style.add("FONTSIZE", (0, 0), (-1, 0), 8)

                if well_results.call in _PDF.RESULTS_COLOR_CODE:
                    cell_style.add(
                        "TEXTCOLOR",
                        (0, 1),
                        (0, 1),
                        _PDF.RESULTS_COLOR_CODE[well_results.call],
                    )

                plate_map_dict[row][col] = Table(
                    [(well_results.accession,), (well_results,), tuple(ct_results)],
                    style=cell_style,
                )

    plate_map_data = [["", *(col for col in COLS_96)]]
    plate_map_data.extend(
        [row, *(plate_map_dict[row].get(col, "") for col in COLS_96)] for row in ROWS_96
    )

    # this table will fill an entire landscape page
    plate_map = Table(
        plate_map_data,
        colWidths=[0.3 * inch] + [0.8 * inch] * 12,
        rowHeights=[0.3 * inch] + [0.8 * inch] * 8,
        style=table_style,
    )

    return plate_map


def format_metadata_table(results: ProcessingResults, styles):
    """
    Formats a table of metadata. We have both final and diagnostic information in
    here, in two columns for readability and to save some vertical space.
    """

    metadata_table_style = TableStyle(
        [
            ("SPAN", (0, 0), (1, 0)),  # 2 columns for first header
            ("SPAN", (2, 0), (3, 0)),  # 2 columns for second header
            ("FONT", (0, 0), (-1, 0), styles["Heading1"].fontName),  # bold header
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
    )

    metadata = [
        ["Run Information", "", "Diagnostic Information", ""],
        [
            "96 Sample Plate:",
            results.bravo_metadata.sample_barcode,
            "96 RNA Plate:",
            results.bravo_metadata.rna_barcode,
        ],
        [
            "Completed at:",
            results.completion_time,
            "384 PCR Plate:",
            results.bravo_metadata.pcr_barcode,
        ],
        [
            "Run by:",
            results.bravo_metadata.researcher,
            "Bravo station ID:",
            results.bravo_metadata.bravo_station,
        ],
        [
            "Controls:",
            results.controls.upper(),
            "qPCR station ID:",
            results.bravo_metadata.qpcr_station,
        ],
    ]

    metadata_table_style.add(
        "TEXTCOLOR", (1, 4), (1, 4), _PDF.CONTROLS_COLOR_CODE[results.controls]
    )

    metadata_table = Table(
        metadata,
        colWidths=[1.25 * inch, 2.75 * inch] * 2,
        spaceBefore=0.25 * inch,
        spaceAfter=0.25 * inch,
        style=metadata_table_style,
    )

    return metadata_table


def format_ct_curves(results: ProcessingResults):
    fig = plot_ct_curves(results)

    imgdata = BytesIO()
    fig.savefig(imgdata, format="svg", bbox_inches="tight")
    imgdata.seek(0)  # rewind the data
    drawing = svg2rlg(imgdata)

    return drawing


def format_background_ct_curves(results: ProcessingResults, styles):
    plots = []

    for fluor in results.protocol.mapping:
        fig = plot_background_ct_curves(results, fluor)

        imgdata = BytesIO()
        fig.savefig(imgdata, format="svg", bbox_inches="tight")
        imgdata.seek(0)  # rewind the data
        drawing = svg2rlg(imgdata)

        plots.extend(
            [
                PageBreak(),
                Paragraph(
                    f"{results.combined_barcode} - Background Ct Curves: {fluor}",
                    styles["Title"],
                ),
                drawing,
            ]
        )

    return plots


def format_internal_notes(results: ProcessingResults, styles):
    sheet_names = [
        "Sample Plate Metadata",
        "Starting Bravo",
        "Bravo RNA Extraction",
        "qPCR Metadata",
        "Re-run RNA Plate",
    ]
    to_check = [
        results.bravo_metadata.sample_plate_metadata_notes,
        results.bravo_metadata.starting_bravo_notes,
        results.bravo_metadata.bravo_rna_notes,
        results.bravo_metadata.qpcr_notes,
        results.bravo_metadata.bravo_rerun_notes,
    ]

    notes_data = []
    row_heights = []
    for sheet, note_value in zip(sheet_names, to_check):
        if note_value:
            body = note_value.to_html()
            row = (sheet, Paragraph(body, styles["Normal"]))
            notes_data.append(row)
            inches = math.ceil(len(body) / 90) * 0.3 * inch
            row_heights.append(inches)

    # Formatting
    if not notes_data:
        style = ParagraphStyle(name="Center", alignment=1)
        return Paragraph("No Notes", style)

    table_style = TableStyle(
        [
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONT", (0, 0), (0, -1), styles["Heading1"].fontName,),  # bold left column
        ]
    )

    table = Table(
        notes_data,
        colWidths=[1.75 * inch] + [5.5 * inch],
        rowHeights=row_heights,
        spaceBefore=0.25 * inch,
        style=table_style,
    )

    return table


def format_notes(
    rna_description: str,
    qpcr_description: str,
    sample_metadata: str,
    notable_wells: Mapping[str, Sequence[str]],
    styles,
) -> Table:
    rna_description_text = html.escape(rna_description or "")
    qpcr_description_text = html.escape(qpcr_description or "")
    sample_metadata_text = html.escape(sample_metadata or "")

    table_data = [
        [
            Paragraph(
                f"<b>Extraction Description:</b> {rna_description_text}",
                styles["BodyText"],
            )
        ],
        [
            Paragraph(
                f"<b>qPCR Description:</b> {qpcr_description_text}", styles["BodyText"]
            )
        ],
        [
            Paragraph(
                f"<b>Sample Source:</b> {sample_metadata_text}", styles["BodyText"]
            )
        ],
        [Paragraph("<b>Notable Results:</b>", styles["BodyText"])],
    ]
    table_styles = [
        ("LEFTPADDING", (0, 0), (0, -1), 0.5 * inch),
        ("SPAN", (0, 0), (-1, 0)),
        ("SPAN", (0, 1), (-1, 1)),
        ("SPAN", (0, 2), (-1, 2)),
        ("SPAN", (0, 3), (-1, 3)),
    ]

    groups = (
        (Call.POS, "Positive"),
        (Call.POS_REVIEW, "Positive, review required"),
        (Call.POS_CLUSTER, "Positive by cluster"),
        (Call.POS_HOTWELL, "Positive by hot well"),
        (Call.IND, "Indeterminates"),
        (Call.INV, "Invalids"),
    )

    initial_len = len(table_data)

    # add rows for "notable results": all of the positive sample, as well as
    # anything that needs review or will be rerun.
    for group_key, group_label in groups:
        for ix, sample in enumerate(notable_wells[group_key]):
            # if this is the beginning of a section (ix == 0) and there is a group of
            # samples above this (len(table_data) > initial_len), we add a line to
            # separate the groups.
            if ix == 0 and len(table_data) > initial_len:
                row_id = len(table_data)
                table_styles.append(
                    ("LINEABOVE", (1, row_id), (-1, row_id), 1, colors.black)
                )

            # add the sample id (and the label, if this is the first row in the group)
            table_data.append(["", group_label if ix == 0 else "", sample])

    if len(table_data) == initial_len:
        # nothing to report
        table_data.append(["", "None", ""])
        row_id = len(table_data) - 1
        table_styles.append(("SPAN", (1, row_id), (-1, row_id)))

    table_data.append([Paragraph("<b>Comments:</b> ", styles["BodyText"])])
    row_id = len(table_data) - 1
    table_styles.append(("SPAN", (0, row_id), (-1, row_id)))

    table = Table(
        table_data,
        colWidths=[1.5 * inch, 1.75 * inch, 4.75 * inch],
        style=TableStyle(table_styles),
    )

    return table
