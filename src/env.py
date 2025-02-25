
from os import getenv
import multiprocessing as mp


NAMESPACE_EXCLUDE_FILTER = getenv('NAMESPACE_EXCLUDE_FILTER') or 'kube-system|kubestash-v2'
TABLE = getenv('TABLE') or ''
TABLE_REGION = getenv('TABLE_REGION') or ''
PROJECT_ID = getenv('PROJECT_ID') or ''
GCP_INSTANCE_ID = getenv('GCP_INSTANCE_ID') or ''
STREAM_ARN = getenv('STREAM_ARN') or ''
CLUSTER_NAME = getenv('CLUSTER_NAME') or ''
VERBOSE = getenv('VERBOSE') or ''
DRY_RUN = getenv('DRY_RUN') or ''
NODE_IP = getenv('NODE_IP') or ''
# Actual wait time to wait before starting the DDB fetch operation
WAIT_TIME = int(getenv('WAIT_TIME', "120")) or 120
HTTP_TIMEOUT = int(getenv('HTTP_TIMEOUT', "15")) or 15
CREDSTASH_SYNC_TIMEOUT_SECS = int(getenv('CREDSTASH_SYNC_TIMEOUT_SECS', "300")) or 300
UPDATING_SECRETS = mp.Value('i', 1)
FLASK_API_KEY = getenv('FLASK_API_KEY') or ''
SECRET_BACKEND = getenv('SECRET_BACKEND') or 'dynamodb'