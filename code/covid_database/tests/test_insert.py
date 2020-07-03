from covid_database.models.qpcr_processing import BravoStation


def test_insert_single(session):
    """Test inserting a single row into a single table. This will eventually get
    replaced with an actual test insert into the schema based on sample data"""

    new_station = BravoStation(name="clia-bravo-1")

    session.add(new_station)

    # Query it!
    query = (
        session.query(BravoStation).filter(BravoStation.name == "clia-bravo-1").one()
    )

    assert query is not None
