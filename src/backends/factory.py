# src/factories/secret_sync_factory.py

from backends.dynamodb_sync import DynamoDBSecretSync
from backends.bigtable_sync import BigtableSecretSync


class SecretSyncFactory:
    @staticmethod
    def get_sync_backend(backend: str, **kwargs):
        if backend == "dynamodb":
            return DynamoDBSecretSync(
                region=kwargs.get("region"),
                table_name=kwargs.get("table_name"),
            )
        elif backend == "bigtable":
            return BigtableSecretSync(
                project_id=kwargs.get("project_id"),
                instance_id=kwargs.get("instance_id"),
                table_id=kwargs.get("table_id"),
            )
        else:
            raise ValueError(f"Unsupported backend: {backend}")
