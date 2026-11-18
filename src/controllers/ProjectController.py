# ======================================================
# Import Libs
# ======================================================

from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignal
import os


# ======================================================
# Func.
# ======================================================
# - ProjectController — resolve project folders on disk
#   - __init__ — initialize instance state and dependencies
#   - get_project_path — build the filesystem path for a project
# ======================================================

class ProjectController(BaseController):
    
    def __init__(self):
        super().__init__()

    def get_project_path(self, project_id: str):
        project_dir = os.path.join(
            self.files_dir,
            str(project_id)
        )

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        return project_dir

    
