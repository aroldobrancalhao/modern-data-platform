from enum import StrEnum


class PipelineStage(StrEnum):
    INGESTION = "ingestion"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    WAREHOUSE = "warehouse"
    SEMANTIC = "semantic"