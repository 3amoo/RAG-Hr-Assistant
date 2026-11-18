# ======================================================
# Import Libs
# ======================================================

from helpers.config import get_settings, Settings


# ======================================================
# Func.
# ======================================================
# - BaseDataModel — common session-aware DAO base class
#   - __init__ — initialize instance state and dependencies
# ======================================================

class BaseDataModel:

    def __init__(self, db_client: object):
        self.db_client = db_client
        self.app_settings = get_settings()
