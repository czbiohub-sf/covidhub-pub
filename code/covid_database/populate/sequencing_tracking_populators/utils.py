from covid_database.models.ngs_sample_tracking import Project


class ProjectHandler:
    def __init__(self, session):
        projects = session.query(Project).all()
        self.project_ids_to_models = {
            result.rr_project_id: result for result in projects
        }

    def get_project_from_czb_id(self, czb_id):
        for rr_project_code, project in self.project_ids_to_models.items():
            if rr_project_code in czb_id:
                return project
        return None


CONTROL_NAMES = {"water", "ntc", "hrc", "pc", "pbs", "hela"}


def check_control(czb_id):
    """return true if the czb_id is a control value"""
    czb_id = czb_id.lower()
    for control_val in CONTROL_NAMES:
        if control_val in czb_id:
            return True
    return False
