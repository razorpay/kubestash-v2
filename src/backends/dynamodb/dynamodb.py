from interfaces.secret_sync_interface import SecretSyncInterface


class DynamoDBSecretSync(SecretSyncInterface):
    def __init__(self, region: str, table_name: str):
        self.region = region
        self.table_name = table_name

    def fetch_secrets(self):
        session_params = credstash.get_session_params(None, None)
        secret = credstash.getAllSecrets('', region=region, table=table, **session_params)
        final_dict = {}
        for key in secret.keys():
            if validate_key(key):
                namespace, secret_name, secret_key = key.split("/")
                secret_key = stringFormatK8s(secret_key)
                secret_value = base64.b64encode(secret[key].encode('utf-8')).decode("utf-8")
                if namespace not in final_dict:
                    final_dict[namespace] = {secret_name: {secret_key: secret_value}}
                else:
                    if secret_name not in final_dict[namespace]:
                        final_dict[namespace][secret_name] = {secret_key: secret_value}
                    else:
                        final_dict[namespace][secret_name][secret_key] = secret_value
            else:
                if VERBOSE:
                    print("Helper:Not a valid key[Ignoring]: ", key)
        return final_dict