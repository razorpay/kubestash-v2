from env import UPDATING_SECRETS, SECRET_BACKEND, GCP_INSTANCE_ID
from helpers.k8s import K8Helper, getKeyListFromDict,getFinalDictionary
from factory import SecretSyncFactory

# Init to start the syncing of secrets
@PROMETHEUS_METRICS['secret_fetch_time'].time()
def syncSecretFromBackend(updating_secrets = UPDATING_SECRETS):
  print("Helper:Starting the syncing of Secrets in {} cluster...".format(CLUSTER_NAME))
  secrets_data = {}
  ns_in_k8s = []

  print("Helper:Fetching the Data from the DDB/BIGTABLE. Little longer wait time expected !!!")
  updating_secrets.value = 1

  backend = SecretSyncFactory.get_sync_backend(SECRET_BACKEND)

  try:
    secrets_data = func_timeout(CREDSTASH_SYNC_TIMEOUT_SECS, backend.fetch_secrets , args=(TABLE_REGION, DDB_TABLE, GCP_INSTANCE_ID))
  except FunctionTimedOut as e:
    print("Helper:Timeout of {} secs while trying to fetch data from credstash.".format(CREDSTASH_SYNC_TIMEOUT_SECS))
    statusFile("Fail")
    PROMETHEUS_METRICS['table_fetch_status'].inc()
    raise Exception

  k8s_helper = K8Helper()

  try:
    ns_in_k8s = k8s_helper.describe_all_ns()
  except Exception as e:
    print("Helper:Exception while trying to describe all namespaces in kubernetes. %s\n" % e)
    statusFile("Fail")
    raise Exception

  listFromDDBdict = getKeyListFromDict(ddb_data)
  excludeNsList = k8s_helper.parseExcludeNsFilter()
  actualNsList = k8s_helper.getActualNSList(listFromDDBdict, ns_in_k8s, excludeNsList)
  if VERBOSE:
    print("Helper:Syincing in following Namespace:", actualNsList)
  finalDictToProcess = getFinalDictionary(ddb_data, actualNsList)
  try:
    addUpdateK8sSecret(finalDictToProcess)
  except Exception as e:
    print("Helper:Exception in updating secrets to k8s. %s\n" % e)
    PROMETHEUS_METRICS['key_synced_status'].inc()
    statusFile("Fail")
    raise Exception
  print("Helper:Completed the syncing of Secrets.")
