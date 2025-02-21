

from os import getenv

from secret_fetcher.bigtable.bigtable import BigtableSecretFetcher
from secret_fetcher.dynamodb.dynamodb import DynamoDBSecretFetcher

def get_secret_fetcher():
    backend = getenv('SECRET_BACKEND', 'dynamodb')  # Default to DynamoDB
    if backend == 'bigtable':
        return BigtableSecretFetcher(
            project_id=getenv('GCP_PROJECT_ID'),
            instance_id=getenv('BIGTABLE_INSTANCE_ID'),
            table_id=getenv('BIGTABLE_TABLE_ID')
        )
    else:
        return DynamoDBSecretFetcher(
            region=getenv('TABLE_REGION'),
            table=getenv('DDB_TABLE')
        )
