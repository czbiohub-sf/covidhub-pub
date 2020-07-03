from sqlalchemy import Column, ForeignKey, Integer, MetaData, String
from sqlalchemy.ext.declarative import declarative_base

import covid_database.models.mixins as mx

meta = MetaData(schema="covidtracker")
CovidTrackerBase = declarative_base(cls=mx.BaseMixin, metadata=meta)


class Group(CovidTrackerBase, mx.NameMixin):
    """
    User groups, for authorization purposes.

    :param name: The name of the group.
    :param auspice_json_s3_path: The s3 path (e.g. directory) that members of the group have access to.
    """

    __tablename__ = "groups"

    auspice_json_s3_path = Column(String, nullable=False)


class UsersGroups(CovidTrackerBase):
    """
    A join table that assigns users to user groups.

    :param user_id: The user id from Auth0.
    :param group_id: The group to assign this user to.
    """

    __tablename__ = "users_groups"

    user_id = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"))
