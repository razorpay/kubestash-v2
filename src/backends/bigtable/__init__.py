from google.cloud import bigtable
from google.cloud.bigtable import row
from interfaces.secret_sync_interface import SecretSyncInterface


class BigtableSecretSync(SecretSyncInterface):
    def __init__(self, project_id: str, instance_id: str, table_id: str):
        self.project_id = project_id
        self.instance_id = instance_id
        self.table_id = table_id
        self.client = bigtable.Client(project=self.project_id, admin=True)
        self.instance = self.client.instance(self.instance_id)
        self.table = self.instance.table(self.table_id)

    def sync_secrets(self):
        print("Syncing secrets from Bigtable to Kubernetes...")
        secrets = self.fetch_secrets()
        # Add logic to update Kubernetes secrets here if needed
        return secrets

    def fetch_secrets(self):
        try:
            print(f"Fetching secrets from Bigtable table: {self.table_id}")
            rows = self.table.read_rows()
            secrets = {}
            for row in rows:
                # Assuming each row key is the secret name and the value is in a specific column
                row_key = row.row_key.decode("utf-8")
                secret_value = row.cells["secrets"]["value"][0].value.decode("utf-8")
                secrets[row_key] = secret_value
            return secrets
        except Exception as e:
            print(f"Error fetching secrets from Bigtable: {e}")
            raise
