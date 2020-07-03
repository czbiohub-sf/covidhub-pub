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
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

import covid_database.models.enums as enums
import covid_database.models.mixins as mx
from covid_database.models.qpcr_processing import QPCRProcessingBase, RNAPlate

meta = MetaData(schema="ngs_sample_tracking")
NGSTrackingBase = declarative_base(cls=mx.BaseMixin, metadata=meta)


class Project(NGSTrackingBase, mx.NameMixin):
    """One of the collaborator sites we get samples from.

   :param name: The name of the site
   :param site_number: The site number associated
   """

    __tablename__ = "projects"

    rr_project_id = Column(String, unique=True, nullable=False)
    type = Column(ENUM(enums.NGSProjectType))
    cliahub_site_id = Column(String)
    collaborating_institution = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    contract_status = Column(ENUM(enums.ContractStatus))
    public = Column(Boolean)
    objective = Column(String)
    microbial_allowed = Column(Boolean, nullable=False)
    sars_cov2_allowed = Column(Boolean, nullable=False)
    transcriptome_allowed = Column(Boolean, nullable=False)


class CZBID(NGSTrackingBase):
    GENERIC_PARAMS = ""
    """A single czb_id which is just a barcode.
    """

    __doc__ = f"""A generic Plate that has a barcode and optional notes attached to it
        {GENERIC_PARAMS}"""

    __tablename__ = "czb_ids"

    czb_id = Column(String(50), nullable=False, unique=True)
    czb_id_type = Column(String(50))

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project = relationship(Project, backref=backref("czb_ids", uselist=True))

    __mapper_args__ = {"polymorphic_identity": "czb_ids", "polymorphic_on": czb_id_type}

    def __repr__(self):
        return f"<{self.czb_id_type} -{self.czb_id}>"


class InternalCZBID(CZBID):
    f"""OG plates
        {CZBID.GENERIC_PARAMS}
    """
    __tablename__ = "cherry_picked_czb_ids"

    id = Column(Integer, ForeignKey("czb_ids.id"), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "cherry_picked_czb_ids"}


class CollaboratorCZBID(CZBID):
    f"""OG plates
        {CZBID.GENERIC_PARAMS}
   :param collection_date: date the sample was collected
   :param specimen_source: source on the body the sample was taken from
   :param initial_volume: the initial volume of the sample
   :param zip_prefix: first 3 digits of patient zipcode
    """
    __tablename__ = "collaborator_czb_ids"

    id = Column(Integer, ForeignKey("czb_ids.id"), primary_key=True)

    external_accession = Column(String(50), nullable=False)
    specimen_source = Column(String)
    collection_date = Column(DateTime)
    initial_volume = Column(Float)
    zip_prefix = Column(String(3))
    notes = Column(String)

    __mapper_args__ = {"polymorphic_identity": "collaborator_czb_ids"}


class DphCZBID(CZBID):
    f"""OG plates
    {CZBID.GENERIC_PARAMS}

   :param shipping_container: the shipping container the sample came in with
   :param specimen_source: source on the body the sample was taken from
   :param collection_date: date the sample was collected
   :param tested_date: date the sample was qpcr tested
   :param zip_prefix: first 3 digits of patient zipcode
   :param initial_volume: the initial volume of the sample
   :param extraction_method: type of extraction method used for testing
   """

    __tablename__ = "dph_czb_ids"

    id = Column(Integer, ForeignKey("czb_ids.id"), primary_key=True)

    external_accession = Column(String(50), nullable=False)
    specimen_source = Column(String)
    collection_date = Column(DateTime, nullable=False)
    tested_date = Column(DateTime)
    zip_prefix = Column(String(3))
    initial_volume = Column(Float)
    extraction_method = Column(String)
    container_name = Column(String)
    date_received = Column(DateTime)

    __mapper_args__ = {"polymorphic_identity": "dph_czb_ids"}


class CZBIDThaw(NGSTrackingBase):
    """
    This object records the volume removed for each czb_id after an plate thaw action.

    :param czb_id: one-to-one relationship to a czb_id
    :param volume_removed: the volume removed for the specific czb_id and plate thaw action
    """

    __tablename__ = "czb_id_to_thaws"

    czb_id_id = Column(Integer, ForeignKey("czb_ids.id"), primary_key=True)
    czb_id = relationship(CZBID, backref=backref("thaw", uselist=True))
    volume_removed = Column(Float)


class CZBIDRnaPlate(NGSTrackingBase, mx.NotesMixin):
    """
    This object records the rna_plate+czb_id association that defines a
   tested well from the biohub.

   :param well_id: well in the 96-well plate holding this accession
   :param czb_id: one-to-one relationship czb_id to an rna plate
   :param rna_plate: many-to-one relationship rna plate to czb_ids
   :param notes: Any notes associated with the accession
   """

    __tablename__ = "czb_id_to_rna_plate"

    well_id = Column(Enum(enums.WellId96))

    czb_id_id = Column(Integer, ForeignKey("czb_ids.id"), primary_key=True, unique=True)
    czb_id = relationship(
        CZBID, backref=backref("qpcr_processing.rna_plates", uselist=False)
    )
    rna_plate_id = Column(
        Integer,
        ForeignKey(
            QPCRProcessingBase.metadata.tables["qpcr_processing.rna_plates"].columns.id
        ),
        primary_key=True,
    )
    rna_plate = relationship(RNAPlate, backref=backref("czb_ids", uselist=True))

    def __repr__(self):
        return f"<{self.czb_id.czb_id} ({self.rna_plate.barcode} {self.well_id})>"


class QPCRCollaboratorCqValue(NGSTrackingBase):
    """A specific ct value from a Collaborator result for a specific gene value

    :param qpcr_collaborator_result: many-to-one relationship to an qpcr_collaborator_result
    :param gene_value: the associated gene
    :param cq_value: the reading from the qpcr machine
    """

    __tablename__ = "qpcr_collaborator_ct_values"
    czb_id_id = Column(Integer, ForeignKey("czb_ids.id"))
    czb_id = relationship(
        CZBID, backref=backref("qpcr_collaborator_result", uselist=False)
    )
    gene_value = Column(String)
    cq_value = Column(Float)
    host = Column(Boolean, default=False)


class Plate(NGSTrackingBase, mx.BarcodeMixin, mx.NotesMixin):
    GENERIC_PARAMS = """
    :param plate_type: a string denoting the type of plate (used for polymorphism)
    :param barcode: a required barcode string for tracking this plate
    :param notes: any notes that the researcher may have recorded
    """

    __doc__ = f"""A generic Plate that has a barcode and optional notes attached to it
    {GENERIC_PARAMS}"""

    __tablename__ = "plates"

    plate_type = Column(String(50))

    __mapper_args__ = {"polymorphic_identity": "plates", "polymorphic_on": plate_type}

    def __repr__(self):
        return f"<{self.plate_type} - {self.barcode}>"


class OgPlate(Plate):
    f"""OG plates
    {Plate.GENERIC_PARAMS}
    :param created_date: date the plate was created
    :param created_by: many to one relationship between lab staff member who created the plate
    """
    __tablename__ = "og_plates"

    id = Column(Integer, ForeignKey("plates.id"), primary_key=True)
    created_date = Column(DateTime)

    created_by = Column(String)
    __mapper_args__ = {"polymorphic_identity": "og_plates"}


class CZBIDOgPlate(NGSTrackingBase):
    """
    This object records the og+czb_id association.

   :param well_id: well in the 96-well plate holding this accession
   :param czb_id: one-to-one relationship to a czb_id
   :param og_plate: many-to-one relationship to og plates
   :param accession: an accession barcode from a collaborator site
   """

    __tablename__ = "czb_id_to_og_plate"

    well_id = Column(Enum(enums.WellId96))

    czb_id_id = Column(Integer, ForeignKey("czb_ids.id"), primary_key=True)
    czb_id = relationship(CZBID, backref=backref("og_plate", uselist=False))

    og_plate_id = Column(Integer, ForeignKey("og_plates.id"), primary_key=True,)
    og_plate = relationship(OgPlate, backref=backref("czb_ids", uselist=True))

    def __repr__(self):
        return f"<{self.czb_id.czb_id} ({self.og_plate.barcode} {self.well_id})>"


class LibraryPlate(Plate):
    f"""Sequencing plates
    {Plate.GENERIC_PARAMS}
    :param created_date: date the plate was created
    """
    __tablename__ = "library_plates"

    id = Column(Integer, ForeignKey("plates.id"), primary_key=True)
    created_date = Column(DateTime)

    __mapper_args__ = {"polymorphic_identity": "library_plates"}


class SequencingPlateCreation(NGSTrackingBase):
    """Table that records when a library plate was used for sequencing"""

    __tablename__ = "library_plates_to_sequencing"
    created_date = Column(DateTime)

    library_plate_id = Column(Integer, ForeignKey("library_plates.id"))
    library_plate = relationship(LibraryPlate, backref="sequencing_plate_created")


class WorkingPlate(Plate):
    f"""Sequencing plates
    {Plate.GENERIC_PARAMS}
    :param created_date: date the plate was created
    """
    __tablename__ = "working_plates"

    id = Column(Integer, ForeignKey("plates.id"), primary_key=True)
    created_date = Column(DateTime)

    __mapper_args__ = {"polymorphic_identity": "working_plates"}


class CZBIDWorkingPlate(NGSTrackingBase):
    """
    This object records the working plate+czb_id association.

   :param well_id: well in the 96-well plate holding this accession
   :param czb_id: one-to-one relationship to a czb_id
   :param working_plate: many-to-one relationship to working_plates
   """

    __tablename__ = "czb_id_to_working_plate"

    well_id = Column(Enum(enums.WellId96))

    czb_id_id = Column(Integer, ForeignKey("czb_ids.id"))
    czb_id = relationship(CZBID, backref=backref("working_plates", uselist=False))
    working_plate_id = Column(
        Integer, ForeignKey("working_plates.id"), primary_key=True,
    )
    working_plate = relationship(WorkingPlate, backref=backref("czb_ids", uselist=True))

    def __repr__(self):
        return f"<{self.czb_id.czb_id} ({self.working_plate.barcode} {self.well_id})>"


class CZBIDLibraryPlate(NGSTrackingBase):
    """
    This object records the library plate+czb_id association.

   :param well_id: well in the 384-well plate holding this accession
   :param czb_id: one-to-one relationship to a czb_id
   :param library_plate: many-to-one relationship to library_plates
   """

    __tablename__ = "czb_id_to_library_plate"

    well_id = Column(Enum(enums.WellId384))

    czb_id_id = Column(Integer, ForeignKey("czb_ids.id"))
    czb_id = relationship(CZBID, backref=backref("library_plates", uselist=False))
    library_plate_id = Column(
        Integer, ForeignKey("library_plates.id"), primary_key=True,
    )
    library_plate = relationship(LibraryPlate, backref=backref("czb_ids", uselist=True))
    indexI5 = Column(String)
    indexI7 = Column(String)

    def __repr__(self):
        return f"<{self.czb_id.czb_id} ({self.library_plate.barcode} {self.well_id})>"


class CZBIDToGisaidData(NGSTrackingBase):
    """
    This object records all the gisaid data available for a czb_id
    """

    __tablename__ = "czb_id_to_gisaid_data"

    czb_id_id = Column(Integer, ForeignKey("czb_ids.id"), primary_key=True)
    czb_id = relationship(CZBID, backref=backref("gisaid_data", uselist=False))

    gisaid_id = Column(String(50), unique=True)
    genbank_accession_id = Column(String(50), unique=True)
    genome_recovered = Column(Boolean)
    filter_stats = Column(String(100))
    combined_stats = Column(String(100))
    mapped_reads = Column(String(100))
    total_reads = Column(String(100))
