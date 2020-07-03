# the main models in the database
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

import covid_database.models.enums as enums
import covid_database.models.mixins as mx
from covidhub.constants.enums import ControlsMappingType

meta = MetaData(schema="qpcr_processing")
QPCRProcessingBase = declarative_base(cls=mx.BaseMixin, metadata=meta)


# people, places, protocols, equipment


class Institute(QPCRProcessingBase, mx.NameMixin):
    """One of the institutes involved in the lab.

    :param name: The name of the institute
    """

    __tablename__ = "institutes"


class Researcher(QPCRProcessingBase, mx.NameMixin):
    """Researcher performing, supervising, or otherwise supporting CLIBHub testing.

    :param name: The name of the researcher
    :param institute: the Institute they are affiliated with
    :param supervisor: flag indicating this person is a supervisor
    :param clia_certified: flag indicating this person has been CLIA certified
    """

    __tablename__ = "researchers"

    institute_id = Column(Integer, ForeignKey("institutes.id"))
    institute = relationship("Institute", backref="researchers")

    supervisor = Column(Boolean)
    clia_certified = Column(Boolean)


class BravoStation(QPCRProcessingBase, mx.NameMixin):
    """A Bravo Station

    :param name: the name of the station
    """

    __tablename__ = "bravo_stations"


class QPCRStation(QPCRProcessingBase, mx.NameMixin):
    """A qPCR Station

    :param name: the name of the station
    """

    __tablename__ = "qpcr_stations"


class Fridge(QPCRProcessingBase, mx.NameMixin):
    """A 4°C refrigerator

    :param name: the name of the fridge
    """

    __tablename__ = "fridges"


class Freezer(QPCRProcessingBase, mx.NameMixin):
    """A -80°C freezer

    :param name: the name of the freezer
    """

    __tablename__ = "freezers"


class Reagent(QPCRProcessingBase, mx.NameMixin):
    """One of the reagents used in the testing workflow. Not a specific lot.

    :param name: the name of the reagent
    """

    __tablename__ = "reagents"


# reagent tracking: which plates contain which lots


class ReagentLot(QPCRProcessingBase):
    """A specific lot of a reagent

    :param reagent: many-to-one relationship to Reagent
    :param reagent_lot: a barcode indicating the specific lot number
    """

    __tablename__ = "reagent_lots"

    reagent_id = Column(Integer, ForeignKey("reagents.id"))
    reagent = relationship("Reagent", backref="lots")
    reagent_lot = Column(String(50), nullable=False)
    UniqueConstraint("reagent", "reagent_lot")

    def __repr__(self):
        return f"<{self.reagent.name} - Lot {self.reagent_lot}>"


# association table for many-to-many reagent_prep <-> reagent_lots
plate_reagent_lots = Table(
    "reagent_prep_lots",
    QPCRProcessingBase.metadata,
    Column("lot", ForeignKey("reagent_lots.id"), primary_key=True),
    Column("prep", ForeignKey("plate_preps.id"), primary_key=True),
)


# sample tracking: plates of various kinds


class Plate(QPCRProcessingBase, mx.BarcodeMixin, mx.NotesMixin):
    GENERIC_PARAMS = """
    :param plate_type: a string denoting the type of plate (used for polymorphism)
    :param barcode: a required barcode string for tracking this plate
    :param notes: any notes that the researcher may have recorded
    :param prep: a many-to-one relationship to PlatePrep representing the batch
                 this plate was prepared with and the researcher who did it
    """

    __doc__ = f"""A generic Plate that has a barcode and optional notes attached to it
    {GENERIC_PARAMS}"""

    __tablename__ = "plates"

    plate_type = Column(Enum(enums.PlateType))

    prep_id = Column(Integer, ForeignKey("plate_preps.id"))
    prep = relationship("PlatePrep", backref="plate_preps")

    __mapper_args__ = {"polymorphic_on": plate_type}

    def __repr__(self):
        return f"<{self.plate_type} - {self.barcode}>"


class ReagentPlate(Plate):
    f"""A plate of one or more reagents, used for RNA extraction.
    {Plate.GENERIC_PARAMS}
    :param reagent_plate_type: an Enum denoting the type of reagents in the plate
    :param rna_extraction: a many-to-one relationship with the Extraction this plate
                           was used in
    """
    __tablename__ = "reagent_plates"

    id = Column(Integer, ForeignKey("plates.id"), primary_key=True)

    reagent_plate_type = Column(Enum(enums.ReagentPlateType))
    rna_extraction_id = Column(Integer, ForeignKey("rna_extractions.id"))
    rna_extraction = relationship("Extraction", backref="reagent_plates")

    __mapper_args__ = {"polymorphic_identity": enums.PlateType.REAGENT}


class RNAPlate(Plate):
    f"""An RNA plate. Contains no reagents so will not have a prep, but is used as
    part of the extraction and aliquoting steps.
    {Plate.GENERIC_PARAMS}
    """
    __tablename__ = "rna_plates"

    id = Column(Integer, ForeignKey("plates.id"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": enums.PlateType.RNA}


class SamplePlate(Plate):
    f"""A plate of samples. These plates are Prepped with 2x DNA/RNA shield. They are also
    couriered from CB to CZB and the Registration table records that name and time of
    arrival. A sample plate holds many accessions and can be extracted multiple times.

    {Plate.GENERIC_PARAMS}
    :param registration: the registration information for this sample plate
    :param courier_name: the person who brought this plate to CZB
    :param prepared_at: which lab the sample plate was prepared at
    :param plate_layout_checksum: md5 checksum for the plate layout file
    """
    __tablename__ = "sample_plates"

    id = Column(Integer, ForeignKey("plates.id"), primary_key=True)

    registration_id = Column(Integer, ForeignKey("registrations.id"))
    registration = relationship("Registration", backref="sample_plates")

    prepared_at = Column(Enum(enums.LabLocation))
    plate_layout_checksum = Column(String(50))

    __mapper_args__ = {"polymorphic_identity": enums.PlateType.SAMPLE}


class QPCRPlate(Plate):
    f"""qPCR plates are Prepped with reagents based on the the version of the plate.
    A QPCRPlate will be associated with one sample plate via an Aliquoting entry
    {Plate.GENERIC_PARAMS}
    :param protocol: which SOP this qpcr plate is prepared for: defines the reagents
    """
    __tablename__ = "qpcr_plates"

    id = Column(Integer, ForeignKey("plates.id"), primary_key=True)

    protocol = Column(Enum(enums.Protocol))

    __mapper_args__ = {"polymorphic_identity": enums.PlateType.QPCR}


class AccessionSample(QPCRProcessingBase, mx.NotesMixin):
    """This object records the sample_plate+accession barcode that defines a
    tested well, including information such as the location and well id. This is how we
    store sample plate layouts.

    :param well_id: well in the 96-well plate holding this accession
    :param accession: string representation of the sample id. In combination with
                      sample_plate_id, this must be unique
    :param sample_plate: many-to-one relationship to a sample plate
    :param location: the source of this sample
    :param location_submitter_id: the sample used at the originating location
    :param notes: Any notes associated with the accession
    """

    __tablename__ = "accession_to_sample_plate"
    __table_args__ = (UniqueConstraint("accession", "sample_plate_id"),)

    well_id = Column(Enum(enums.WellId96))

    accession = Column(String(6), nullable=False)  # valid accession: [A-Z]\d{1,5}

    sample_plate_id = Column(Integer, ForeignKey("sample_plates.id"), nullable=False)
    sample_plate = relationship(
        "SamplePlate", backref=backref("accessions", cascade="all, delete-orphan")
    )

    location = Column(String(50))
    location_submitter_id = Column(String(50))

    def __repr__(self):
        return f"<{self.accession} ({self.sample_plate.barcode} {self.well_id})>"


class LocationFileChecksums(QPCRProcessingBase):
    """Stores the checksums of the accession location files that have already been
    processed

    :param csv_checksum: md5 for each file already read from drive
    """

    __tablename__ = "location_file_checksums"
    csv_checksum = Column(String(32))


# lab procedures: reagent prep, extraction, aliquoting (reruns), and qpcr
class Registration(
    QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin
):
    """Registration tracks the arrival of sample plates at CLIAHUB for
    processing. This includes both plates made externally and plates made
    internally.

    :param timestamp: the time the plate was marked as arrived for testing
    :param notes: notes regarding the registration of these sample plates
    :param researcher: the researcher who marked these plates as arrived
    :param courier_name: name of courier who delivered samples
    """

    __tablename__ = "registrations"

    courier_name = Column(String(50))

    def __repr__(self):
        return f"<Registration for sample plates {self.sample_plates} at {self.created_at}>"


class SamplePlateMetadata(
    QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin
):
    """Tracks the upload of sample plate plate maps and other
    metadata associated with sample plates.

    SamplePlateMetadata is 1:1 with SamplePlate

    :param timestamp: timestamp of metadata submission
    :param researcher: the researcher submitting metadata
    :param sample_plate_type: the type of sample plate, clinical, validation, or experimental
    :param controls_type: control layout scheme for this plate
    :param sample_source: sample originating lab
    :param plate_layout_format: format of plate layout being submitted
    """

    __tablename__ = "sample_plate_metadata"

    sample_plate_id = Column(Integer, ForeignKey("sample_plates.id"))
    sample_plate = relationship(
        "SamplePlate", backref=backref("metadata", uselist=False)
    )

    sample_plate_type = Column(Enum(enums.SamplePlateType))

    controls_type = Column(Enum(ControlsMappingType))

    sample_source = Column(String(255))

    plate_layout_format = Column(Enum(enums.PlateMapType))

    def __repr__(self):
        return f"<SamplePlateMetadata for {self.sample_plate.barcode}>"


class PlatePrep(
    QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin
):
    """PlatePrep is a many-to-many association object linking reagent lots to the
    set of plates that are prepared as a group

    :param timestamp: the time this prep was performed
    :param researcher: the researcher who made the plates
    :param notes: any notes they recorded during the prep
    :param reagent_lots: many-to-many relationship with lots of reagents
    """

    __tablename__ = "plate_preps"

    reagent_lots = relationship(
        "ReagentLot", secondary=plate_reagent_lots, backref="preps"
    )


class Extraction(
    QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin
):
    """Extraction is an association object linking sample plates to RNA plates. A
    single sample plate can be extracted multiple times, but an RNA plate is only
    extracted into once.

    :param timestamp: the time this prep was performed
    :param researcher: the researcher who made the plates
    :param notes: any notes they recorded during the prep
    :param bravo: the bravo station used for the extraction
    :param sample_plate: many-to-one relationship to SamplePlate
    :param rna_plate: the plate that the RNA was extracted into
    """

    __tablename__ = "rna_extractions"

    bravo_id = Column(Integer, ForeignKey("bravo_stations.id"), nullable=False)
    bravo = relationship("BravoStation", backref="rna_extractions")

    sample_plate_id = Column(Integer, ForeignKey("sample_plates.id"), nullable=False)
    sample_plate = relationship("SamplePlate", backref="rna_extractions")

    rna_plate_id = Column(Integer, ForeignKey("rna_plates.id"), nullable=False)
    rna_plate = relationship(
        "RNAPlate", backref=backref("rna_extraction", uselist=False)
    )

    cliahub_researcher_id = Column(
        Integer, ForeignKey("researchers.id"), nullable=False
    )
    cliahub_researcher = relationship(
        "Researcher", foreign_keys=[cliahub_researcher_id], backref="clia_extractions",
    )

    def __repr__(self):
        return f"<{self.sample_plate.barcode} extracted into {self.rna_plate.barcode}>"


class Aliquoting(
    QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin
):
    """Many-to-one association object linking RNA plates to multiple qpcr plates.
    There is no google form for this object but we can infer its existence from
    the initial RNA extraction (requires one aliquoting) and any RNA reruns. One
    RNA plate can be aliquoted multiple times into different qPCR plates.

    :param timestamp: the time this prep was performed
    :param researcher: the researcher who made the plates
    :param notes: any notes they recorded during the prep
    :param bravo: the bravo station used for the extraction
    :param rna_plate: many-to-one relationship to the source RNA plate
    :param qpcr_plate: the destination qPCR plate
    """

    __tablename__ = "aliquotings"

    bravo_id = Column(Integer, ForeignKey("bravo_stations.id"))
    bravo = relationship("BravoStation", backref="aliquotings")

    rna_plate_id = Column(Integer, ForeignKey("rna_plates.id"))
    rna_plate = relationship("RNAPlate", backref="aliquotings")

    qpcr_plate_id = Column(Integer, ForeignKey("qpcr_plates.id"))
    qpcr_plate = relationship("QPCRPlate", backref=backref("aliquoting", uselist=False))

    def __repr__(self):
        return f"<{self.rna_plate.barcode} aliquoted into {self.qpcr_plate.barcode}>"


class QPCRRun(QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin):
    """A single qPCR run, which links a QPCRPlate to the data. Each well in the original
    sample_plate has a result object, which itself contains the data for the different
    genes and fluors used by the protocol

    :param timestamp: the time this prep was performed
    :param researcher: the researcher who made the plates
    :param notes: any notes they recorded during the prep
    :param steved: boolean recording that the results of this run were steved
    :param qpcr: many-to-one relationship to the qPCR station where it was run
    :param qpcr_plate: the qPCR plate that was run
    :param protocol: which SOP this plate was run under
    :param csv_checksum: md5 checksum for the results csv
    """

    __tablename__ = "qpcr_runs"

    steved = Column(Boolean)

    qpcr_id = Column(Integer, ForeignKey("qpcr_stations.id"))
    qpcr = relationship("QPCRStation", backref="qpcr_runs")

    qpcr_plate_id = Column(Integer, ForeignKey("qpcr_plates.id"))
    qpcr_plate = relationship("QPCRPlate", backref=backref("qpcr_run", uselist=False))

    protocol = Column(Enum(enums.Protocol))

    completed_at = Column(DateTime)
    csv_checksum = Column(String(32))

    def __repr__(self):
        return f"<{self.qpcr_plate.barcode} run on {self.qpcr.name}>"

    @property
    def sample_plate(self):
        return self.qpcr_plate.aliquoting.rna_plate.rna_extraction.sample_plate


class QPCRResult(QPCRProcessingBase):
    """Records the result (call) for a single accession or control in a run. Represents
    a collection of four wells on the 384 well plate.

    :param well_id: well in the 96-well plate holding this result
    :param control_type: an Enum denoting which type of control this is (optional)
    :param call: the call (Pos, Inv, Ind, or Pass/Fail for control)
    :param qpcr_run: many-to-one relationship to the qpcr run
    """

    __tablename__ = "qpcr_results"

    well_id = Column(Enum(enums.WellId96))
    control_type = Column(Enum(enums.ControlType))

    call = Column(Enum(enums.Call))

    qpcr_run_id = Column(Integer, ForeignKey("qpcr_runs.id"))
    qpcr_run = relationship("QPCRRun", backref="qpcr_results")

    def __repr__(self):
        return f"<{self.well_id} - {self.call}>"


class FluorValue(QPCRProcessingBase):
    """A specific value from the qpcr: one fluor from one well

    :param qpcr_result: many-to-one relationship to the qpcr result
    :param fluor: Enum representing the fluorophore measured
    :param position: relative positive (A1, A2, B1, B2) of this well
    :param cq_value: the reading from the qpcr machine
    """

    __tablename__ = "fluor_values"

    qpcr_result_id = Column(Integer, ForeignKey("qpcr_results.id"))
    qpcr_result = relationship("QPCRResult", backref="fluor_values")

    fluor = Column(Enum(enums.Fluor))
    position = Column(Enum(enums.MappedWell))
    cq_value = Column(Float)

    def __repr__(self):
        return (
            f"<{self.qpcr_result.well_id} - {self.fluor} "
            f"({self.position}) - {self.cq_value:.3g}>"
        )


# tracking and waste management


class FridgeCheckin(
    QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin
):
    """Records when a Sample Plate was checked into a fridge

    :param timestamp: time of check-in
    :param researcher: many-to-one relationship to researcher doing the check-in
    :param notes: any notes recorded during the check-in
    :param sample_plate: one-to-one relationship to a sample plate
    :param fridge: many-to-one relationship to the 4°C fridge
    :param shelf: shelf of the fridge
    :param rack: rack in that shelf
    :param plate: the plate (fridge-specific storage) holding the stored Plate
    """

    __tablename__ = "fridge_checkins"

    sample_plate_id = Column(Integer, ForeignKey("sample_plates.id"))
    sample_plate = relationship(
        "SamplePlate", backref=backref("checked_in_4c", uselist=False)
    )

    fridge_id = Column(Integer, ForeignKey("fridges.id"))
    fridge = relationship("Fridge", backref="sample_plates")

    shelf = Column(Integer)
    rack = Column(Integer)
    plate = Column(Integer)

    def __repr__(self):
        return f"<{self.sample_plate.barcode} checked in to {self.fridge}>"


class FreezerCheckin(
    QPCRProcessingBase,
    mx.TimestampMixin,
    mx.ResearcherMixin,
    mx.NotesMixin,
    mx.PlateMixin,
):
    """Records when a Plate (RNA or Sample) was checked into a freezer

    :param timestamp: time of check-in
    :param researcher: many-to-one relationship to researcher doing the check in
    :param notes: any notes recorded during the check-in
    :param plate: one-to-one relationship to an rna or sample plate
    :param freezer: many-to-one relationship to the -80°C freezer
    :param shelf: shelf of the fridge
    :param rack: rack in that shelf
    :param block: block of plates in that rack
    """

    __tablename__ = "freezer_checkins"

    freezer_id = Column(Integer, ForeignKey("freezers.id"))
    freezer = relationship("Freezer", backref="plate_checkins")

    shelf = Column(Integer)
    rack = Column(Integer)
    block = Column(Enum(enums.FreezerBlock))

    def __repr__(self):
        return f"<{self.plate.barcode} checked in to {self.freezer}>"


class FreezerCheckout(
    QPCRProcessingBase,
    mx.TimestampMixin,
    mx.ResearcherMixin,
    mx.PlateMixin,
    mx.NotesMixin,
):
    """Records when a Plate (RNA or Sample) was checked out of a freezer

    :param timestamp: time of check-out
    :param researcher: many-to-one relationship to researcher doing the check out
    :param plate: many-to-one relationship to an rna or sample plate
    :param freezer: many-to-one relationship to the -80°C freezer
    """

    __tablename__ = "freezer_checkouts"

    freezer_id = Column(Integer, ForeignKey("freezers.id"))
    freezer = relationship("Freezer", backref="plate_checkouts")

    def __repr__(self):
        return f"<{self.plate.barcode} checked out of {self.freezer}>"


class WasteManagement(
    QPCRProcessingBase, mx.TimestampMixin, mx.ResearcherMixin, mx.NotesMixin
):
    __tablename__ = "waste_management"

    type = Column(Enum(enums.WasteType))
    __mapper_args__ = {
        "polymorphic_on": type,
    }


class PlateWasteManagement(WasteManagement):
    __tablename__ = "plate_waste_management"

    id = Column(Integer, ForeignKey("waste_management.id"), primary_key=True)
    plate_id = Column("plate_id", ForeignKey("plates.id"), nullable=False)
    plate = relationship("Plate", backref="disposal")

    __mapper_args__ = {"polymorphic_identity": enums.WasteType.PLATES}


class BottleWasteManagement(WasteManagement):
    __tablename__ = "bottle_waste_management"

    id = Column(Integer, ForeignKey("waste_management.id"), primary_key=True)
    bottle_id = Column(Integer, nullable=False)

    __mapper_args__ = {"polymorphic_identity": enums.WasteType.BOTTLES}


class DrumWasteManagement(WasteManagement):
    __tablename__ = "drum_waste_management"

    id = Column(Integer, ForeignKey("waste_management.id"), primary_key=True)
    drum_id = Column(Integer, nullable=False)

    __mapper_args__ = {"polymorphic_identity": enums.WasteType.BAGS}


class LabException(
    QPCRProcessingBase,
    mx.TimestampMixin,
    mx.ResearcherMixin,
    mx.OptionalPlateMixin,
    mx.NotesMixin,
):
    __tablename__ = "exceptions"
