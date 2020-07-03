from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions as func

# a collection of mixin classes to help build the modelss


# everyone needs an auto-generated primary key
class BaseMixin:
    """Base model: all models have integer primary keys"""

    id = Column(Integer, primary_key=True, autoincrement=True)


# for things that have names (people, places, bravos)
class NameMixin:
    """Mixin that adds a required unique name string field"""

    name = Column(String, unique=True)

    def __repr__(self):
        return self.name


# for things with barcodes (various plates)
class BarcodeMixin:
    """Mixin that adds a required barcode string field"""

    barcode = Column(String(50), nullable=False, unique=True)


# for anything we want a timestamp on
class TimestampMixin:
    """Mixin that adds a timestamp. Defaults to time of initialization"""

    created_at = Column(DateTime, default=func.now())


# for things that have free text notes
class NotesMixin:
    """Mixin that adds a free text notes section"""

    notes = Column(Text)


# for things that refer to a Researcher
class ResearcherMixin:
    """Mixin that adds a required foreign key + many-to-one relationship to Researcher"""

    @declared_attr
    def researcher_id(cls):
        return Column("researcher_id", ForeignKey("researchers.id"), nullable=False)

    @declared_attr
    def researcher(cls):
        return relationship(
            "Researcher", foreign_keys=[cls.researcher_id], backref=cls.__tablename__
        )


# for things that refer to a Plate
class PlateMixin:
    """Mixin that adds a required foreign key + many-to-one relationship to Plate"""

    @declared_attr
    def plate_id(cls):
        return Column("plate_id", ForeignKey("plates.id"), nullable=False)

    @declared_attr
    def plate(cls):
        return relationship("Plate", backref=cls.__tablename__)


# for things that optinally refer to a Plate
class OptionalPlateMixin:
    """Mixin that adds an optional foreign key + many-to-one relationship to Plate"""

    @declared_attr
    def plate_id(cls):
        return Column("plate_id", ForeignKey("plates.id"))

    @declared_attr
    def plate(cls):
        return relationship("Plate", backref=cls.__tablename__)
