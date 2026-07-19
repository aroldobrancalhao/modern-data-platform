from dataclasses import dataclass


@dataclass(frozen=True)
class StorageConfig:

    bucket = "mdp-datalake-dev-857854758128"

    bronze_path = f"s3://{bucket}/bronze"
    silver_path = f"s3://{bucket}/silver"
    gold_path = f"s3://{bucket}/gold"

    checkpoints_path = f"s3://{bucket}/checkpoints"
    schemas_path = f"s3://{bucket}/schemas"
    logs_path = f"s3://{bucket}/logs"

    @staticmethod
    def bronze(table_name: str) -> str:
        return f"{StorageConfig.bronze_path}/{table_name}"

    @staticmethod
    def silver(table_name: str) -> str:
        return f"{StorageConfig.silver_path}/{table_name}"

    @staticmethod
    def gold(table_name: str) -> str:
        return f"{StorageConfig.gold_path}/{table_name}"