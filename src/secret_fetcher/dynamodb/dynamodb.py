import base64
from secret_fetcher.secret_fetcher import SecretFetcher


class DynamoDBSecretFetcher(SecretFetcher):
    def __init__(self, region, table):
        self.region = region
        self.table = table

    def fetch_secrets(self):
        session_params = self.get_session_params(None, None)
        secret = self.getAllSecrets('', region=self.region, table=self.table, **session_params)
        return self._process_secrets(secret)
    
    def _process_secrets(self, secret):
        # Existing processing logic from your script
        final_dict = {}
        for key in secret.keys():
            if self.validate_key(key):
                namespace, secret_name, secret_key = key.split("/")
                secret_key = self.stringFormatK8s(secret_key)
                secret_value = base64.b64encode(secret[key].encode('utf-8')).decode("utf-8")
                if namespace not in final_dict:
                    final_dict[namespace] = {secret_name: {secret_key: secret_value}}
                else:
                    final_dict[namespace].setdefault(secret_name, {})[secret_key] = secret_value
        return final_dict
