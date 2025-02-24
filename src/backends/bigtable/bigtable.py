
import base64
from google.cloud import bigtable
from helpers import validate_key
from src.secret_fetcher.secret_fetcher import SecretFetcher

class BigtableSecretFetcher(SecretFetcher):
    def __init__(self, project_id, instance_id, table_id):
        self.client = bigtable.Client(project=project_id, admin=True)
        self.instance = self.client.instance(instance_id)
        self.table = self.instance.table(table_id)

    def fetch_secrets(self):
        rows = self.table.read_rows()
        return self._process_secrets(rows)

    def _process_secrets(self, rows):
        final_dict = {}
        for row in rows:
            key = row.row_key.decode('utf-8')
            if validate_key(key):
                namespace, secret_name, secret_key = key.split("/")
                secret_value = base64.b64encode(row.cells['cf1'][b'secret_value'][0].value).decode('utf-8')
                if namespace not in final_dict:
                    final_dict[namespace] = {secret_name: {secret_key: secret_value}}
                else:
                    final_dict[namespace].setdefault(secret_name, {})[secret_key] = secret_value
        return final_dict