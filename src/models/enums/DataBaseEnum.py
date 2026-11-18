# ======================================================
# Import Libs
# ======================================================

from enum import Enum


# ======================================================
# Func.
# ======================================================
# - DataBaseEnum — database collection constants
# ======================================================

class DataBaseEnum(Enum):

    COLLECTION_PROJECT_NAME = "projects"
    COLLECTION_CHUNK_NAME = "chunks"
    COLLECTION_ASSET_NAME = "assets"

