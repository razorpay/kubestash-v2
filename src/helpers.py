import credstash as cd
from os import getenv
import kubernetes, signal, base64, pytz, re
from kubernetes.client import ApiException
from prometheus_client import Counter, Gauge, Summary
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut


class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, *args):
    self.kill_now = True


# Status Healthy/Fail
def statusFile(code="Healthy"):
  with open('./prom/status', 'w') as fp:
    fp.write(code)


#############################
# Initialize Kubernetes
#############################
try:
    # First, try to use in-cluster config, aka run inside of Kubernetes
    kubernetes.config.load_incluster_config()
except Exception as e:
    try:
        # If we aren't running in kubernetes, try to use the kubectl config file as a fallback
        kubernetes.config.load_kube_config()
    except Exception as ex:
      statusFile("Fail")
      raise ex
kubernetes_core_api  = kubernetes.client.CoreV1Api()

# Filter Format Example: 'ns1|ns2|ns3' or 'ns1'
NAMESPACE_EXCLUDE_FILTER = getenv('NAMESPACE_EXCLUDE_FILTER') or 'kube-system|kubestash-v2'
DDB_TABLE = getenv('DDB_TABLE') or ''
TABLE_REGION = getenv('TABLE_REGION') or ''
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
PROMETHEUS_METRICS = {}
PROMETHEUS_METRICS['settings'] = Counter('kubestash_v2_settings', 'Settings currently used by kubestash',
  ['table_name','table_region', 'cluster_name', 'namespace_exclude_filter', 'http_timeout_seconds', 
    'wait_time_to_sync_ddb_fetch', 'dry_run', 'verbose_enabled', 'node_ip'])
PROMETHEUS_METRICS['settings'].labels(
    table_name = str(DDB_TABLE),
    table_region = str(TABLE_REGION),
    cluster_name = str(CLUSTER_NAME),
    namespace_exclude_filter = str(NAMESPACE_EXCLUDE_FILTER),
    http_timeout_seconds = str(HTTP_TIMEOUT),
    wait_time_to_sync_ddb_fetch = str(WAIT_TIME),
    dry_run = "true" if DRY_RUN else "false",
    verbose_enabled = "true" if VERBOSE else "false",
    node_ip = str(NODE_IP),
  ).inc(0)
PROMETHEUS_METRICS['key_synced_status'] = Gauge(
  'kubestash_key_synced_failed_status', 'Gauge with failed keys. 1 or failed. 0 for normal')
PROMETHEUS_METRICS['key_synced_status'].set(0)
PROMETHEUS_METRICS['table_fetch_status'] = Gauge(
  'kubestash_table_fetch_status', 'Gauge with stucked table status. 1 or failed. 0 for normal')
PROMETHEUS_METRICS['table_fetch_status'].set(0)
PROMETHEUS_METRICS['bad_request_count'] = Counter(
  'kubestash_429_requests_count', 'Counter for bad requests')
PROMETHEUS_METRICS['not_found_count'] = Counter(
  'kubestash_404_request_count', 'Counter for non found requests')
PROMETHEUS_METRICS['malformed_request_count'] = Counter(
  'kubestash_400_request_count', 'Counter for malformed requests')
PROMETHEUS_METRICS['server_error_count'] = Counter(
  'kubestash_500_request_count', 'Counter for internal server error')
PROMETHEUS_METRICS['valid_request_count'] = Counter(
  'kubestash_200_request_count', 'Counter for valid request')
PROMETHEUS_METRICS['ddb_fetch_time'] = Summary(
  'kubestash_ddb_fetch_seconds', 'Time spent fetching DDB data')


# To run jobs in parallel
def run_cpu_tasks_in_parallel(tasks):
    with ProcessPoolExecutor() as executor:
        running_tasks = [executor.submit(task) for task in tasks]
        for running_task in running_tasks:
            try:
              running_task.result()
            except Exception as e:
              print("Helper:Exception in task execution. %s\n" % e)
              statusFile("Fail")


# Return Current UTC time in IST Format
def getcurrentISTtime():
  IST = pytz.timezone('Asia/Kolkata')
  now = datetime.now(IST)
  ist_string = now.strftime("%d/%b/%Y %H:%M:%S IST")
  return ist_string


# Validate if the key is having proper format in DDB
def validate_key(key):
  if len(key.split("/")) == 3:
    namespace, secret_name, secret_key = key.split("/")
    name_pattern = '([a-z0-9-]+)$'
    key_pattern = '([-._a-zA-Z0-9]+)$'
    if re.match(name_pattern, namespace):
      if re.match(name_pattern, secret_name):
        if re.match(key_pattern, secret_key):
          return True
  return False


# Return the UpperCase valid Key format to be updated in k8s
def stringFormatK8s(string):
    return string.replace('-', '_').upper()


# Retruns the dict obj from credstash table
def get_credstash_data(region, table):
  session_params = cd.get_session_params(None, None)
  secret=cd.getAllSecrets('', region=region, table=table, **session_params)
  final_dict = {}
  for key in secret.keys():
    if validate_key(key):
      namespace, secret_name, secret_key = key.split("/")
      secret_key = stringFormatK8s(secret_key)
      secret_value = base64.b64encode(secret[key].encode('utf-8')).decode("utf-8")
      if namespace not in final_dict:
        final_dict[namespace] = { secret_name : { secret_key : secret_value }}
      else:
        if secret_name not in final_dict[namespace]:
          final_dict[namespace][secret_name] = { secret_key : secret_value }
        else:
          final_dict[namespace][secret_name][secret_key] = secret_value
    else:
      if VERBOSE:
        print("Helper:Not a valid key[Ignoring]: ", key)
  return final_dict


# Describe all the namespaces in Kubernetes and return them as list
def describe_all_ns():
  ns_list = []
  try:
    api_response = kubernetes_core_api.list_namespace(
      pretty=True, timeout_seconds=HTTP_TIMEOUT, watch=False)
    for item in api_response.items:
      ns_list.append(item.metadata.name)
  except ApiException as e:
    print("Helper:Exception when calling CoreV1Api -> list_namespace: %s\n" % e)
    statusFile("Fail")
  return ns_list


# Return keys list from dictionary object
def getKeyListFromDict(dictObj):
  return list(dictObj.keys())


# Return the list from the given filter
def parseExcludeNsFilter(filter=NAMESPACE_EXCLUDE_FILTER):
  excludeList = []
  if filter.strip() == "" and len(filter) != 0:
    print("Helper:Exclude Namespace List: Empty List")
    return excludeList
  else:
    if "|" in filter:
      excludeList = [x.strip() for x in filter.split("|")]
      print("Helper:Exclude Namespace List: ", excludeList)
      return excludeList
    else:
      excludeList.append(filter)
      print("Helper:Exclude Namespace List: ", excludeList)
      return excludeList


# Retrun valid list to proceed with Secret Modification
# DDBList = ['ns1', 'ns2', 'ns3']
# K8sList = ['ns1', 'ns3', 'ns4']
# ExcludeNsList = ['ns1']
# DesiredList = ['ns3']
def getActualNSList(DDBList, K8sList, ExcludeNsList):
  actualList = []
  for ns in DDBList:
    if ns in K8sList and ns not in ExcludeNsList:
      actualList.append(ns)
  return actualList


# Retruns the final dicionary to process Secret Modification
def getFinalDictionary(dictObj, actualNsList):
  tmp_dict = dictObj.copy()
  for key in dictObj.keys():
    if key not in actualNsList:
      tmp_dict.pop(key)
  return tmp_dict


# Return k8s Secret Object
def initSecretObject(ns, secret_name, secret_data):
  secret = kubernetes.client.V1Secret()
  secret.data = secret_data
  secret.type = 'Opaque'
  secret.metadata = { 
    'namespace': ns,
    'name': secret_name,
    'annotations': {
      'managedBy': 'kubestashV2',
      'changedAt': getcurrentISTtime()
    }
  }
  return secret


# Update the secrets in k8s cluster
def addUpdateK8sSecret(dictObj):
  PROMETHEUS_METRICS['key_synced_status'].set(0)
  for ns, val_ns in dictObj.items():
    for secret, val_secret in val_ns.items():
      k8s_dict_type = ""
      try:
        api_response = kubernetes_core_api.read_namespaced_secret(secret, ns, pretty=True)
        k8s_dict = api_response.data
        k8s_dict_type = api_response.type
        if k8s_dict_type == "Opaque" and k8s_dict != val_secret:
          if k8s_dict is None:
            k8s_dict = {}
          if len(k8s_dict) > len(val_secret):
            print("Helper:Cluster:{} : Probably manually added key in {} secret in {} namespace is present.".format(CLUSTER_NAME, secret, ns))
          k8s_dict.update(val_secret)
          body = initSecretObject(ns, secret, k8s_dict)
          try:
            if DRY_RUN:
              replace_secret = kubernetes_core_api.replace_namespaced_secret(secret, ns, body, pretty=True, dry_run="All")
              print("Helper:Cluster:{} : DryRun: Will update {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
            else:   
              replace_secret = kubernetes_core_api.replace_namespaced_secret(secret, ns, body, pretty=True)
              print("Helper:Cluster:{} : Updated {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
          except ApiException as e:
            print("Helper:Exception when calling CoreV1Api -> replace_namespaced_secret: %s\n" % e)
            print("Helper:Possible chance for the partial secret update !!!")
            PROMETHEUS_METRICS['key_synced_status'].inc()
            statusFile("Fail")            
        else:
          if k8s_dict_type != "Opaque" and VERBOSE:
            print("Helper:Cluster:{} : Skipping updating {} secret of type {} in {} namespace.".format(CLUSTER_NAME, secret, k8s_dict_type, ns))
          if VERBOSE:
            print("Helper:Cluster:{} : Skipping updating {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
      except ApiException as e:
        body = initSecretObject(ns, secret, val_secret)
        try:
          if DRY_RUN:
            create_secret = kubernetes_core_api.create_namespaced_secret(ns, body, pretty=True, dry_run="All")
            print("Helper:Cluster:{} : DryRun: Will create {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
          else:          
            create_secret = kubernetes_core_api.create_namespaced_secret(ns, body, pretty=True)
            print("Helper:Cluster:{} : Created {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
        except ApiException as e:
          print("Helper:Exception when calling CoreV1Api -> create_namespaced_secret: %s\n" % e)
          print("Helper:Possible chance for the partial secret update !!!")
          PROMETHEUS_METRICS['key_synced_status'].inc()
          statusFile("Fail")


# Init to start the syncing of secrets
@PROMETHEUS_METRICS['ddb_fetch_time'].time()
def syncSecretFromDDB(updating_secrets = UPDATING_SECRETS):
  print("Helper:Starting the syncing of Secrets in {} cluster...".format(CLUSTER_NAME))
  ddb_data = {}
  ns_in_k8s = []

  print("Helper:Fetching the Data from the DDB. Little longer wait time expected !!!")
  updating_secrets.value = 1

  try:
    ddb_data = func_timeout(CREDSTASH_SYNC_TIMEOUT_SECS, get_credstash_data, args=(TABLE_REGION, DDB_TABLE))
  except FunctionTimedOut as e:
    print("Helper:Timeout of {} secs while trying to fetch data from credstash.".format(CREDSTASH_SYNC_TIMEOUT_SECS))
    statusFile("Fail")
    PROMETHEUS_METRICS['table_fetch_status'].inc()
    raise Exception

  try:
    ns_in_k8s = describe_all_ns()
  except Exception as e:
    print("Helper:Exception while trying to describe all namespaces in kubernetes. %s\n" % e)
    statusFile("Fail")
    raise Exception

  listFromDDBdict = getKeyListFromDict(ddb_data)
  excludeNsList = parseExcludeNsFilter()
  actualNsList = getActualNSList(listFromDDBdict, ns_in_k8s, excludeNsList)
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

