# ======================================================
# Import Libs
# ======================================================

from sqlalchemy.future import select

from .BaseDataModel import BaseDataModel
from .db_schemes import Asset


# ======================================================
# Func.
# ======================================================
# - AssetModel — data access for uploaded assets
#   - __init__ — initialize instance state and dependencies
#   - create_instance — build a DAO bound to the current DB session
#   - create_asset — persist a new asset record
#   - get_all_project_assets — list assets belonging to a project
#   - get_asset_record — fetch one asset by id and project
# ======================================================

class AssetModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        return cls(db_client)

    async def create_asset(self, asset: Asset):
        async with self.db_client() as session:
            session.add(asset)
            await session.commit()
            await session.refresh(asset)

        return asset

    async def get_all_project_assets(self, asset_project_id: int, asset_type: str):
        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_type == asset_type,
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

        return records

    async def get_asset_record(self, asset_project_id: int, asset_name: str):
        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name,
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

        return record
