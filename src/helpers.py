import credstash as cd
from os import getenv
import kubernetes, base64, pytz, re
from kubernetes.client import ApiException
from src.helpers.status_file import statusFile
from src.metrics.prometheus_metrics import PROMETHEUS_METRICS
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut
from env import *


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

