import signal
from helpers.status_file import statusFile
from env import NAMESPACE_EXCLUDE_FILTER
import credstash as cd
from os import getenv
import kubernetes, base64, pytz, re
from kubernetes.client import ApiException
from helpers.status_file import statusFile
from metrics.prometheus_metrics import PROMETHEUS_METRICS
from helpers.time import getcurrentISTtime
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut

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


class K8Helper:

    # Describe all the namespaces in Kubernetes and return them as list
    def describe_all_ns(self):
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
    def getActualNSList(self, DDBList, K8sList, ExcludeNsList):
      actualList = []
      for ns in DDBList:
        if ns in K8sList and ns not in ExcludeNsList:
          actualList.append(ns)
      return actualList

    # Return k8s Secret Object
    def initSecretObject(self, ns, secret_name, secret_data):
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

    def addUpdateK8sSecret(self, dictObj):
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
                print("Helper:Cluster:{} : Probably manually added key in {} secret in {} namespace is present.".format(
                  CLUSTER_NAME, secret, ns))
              k8s_dict.update(val_secret)
              body = initSecretObject(ns, secret, k8s_dict)
              try:
                if DRY_RUN:
                  replace_secret = kubernetes_core_api.replace_namespaced_secret(secret, ns, body, pretty=True,
                                                                                 dry_run="All")
                  print(
                    "Helper:Cluster:{} : DryRun: Will update {} secret in {} namespace.".format(CLUSTER_NAME, secret,
                                                                                                ns))
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
                print("Helper:Cluster:{} : Skipping updating {} secret of type {} in {} namespace.".format(CLUSTER_NAME,
                                                                                                           secret,
                                                                                                           k8s_dict_type,
                                                                                                           ns))
              if VERBOSE:
                print(
                  "Helper:Cluster:{} : Skipping updating {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
          except ApiException as e:
            body = self.initSecretObject(ns, secret, val_secret)
            try:
              if DRY_RUN:
                create_secret = kubernetes_core_api.create_namespaced_secret(ns, body, pretty=True, dry_run="All")
                print(
                  "Helper:Cluster:{} : DryRun: Will create {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
              else:
                create_secret = kubernetes_core_api.create_namespaced_secret(ns, body, pretty=True)
                print("Helper:Cluster:{} : Created {} secret in {} namespace.".format(CLUSTER_NAME, secret, ns))
            except ApiException as e:
              print("Helper:Exception when calling CoreV1Api -> create_namespaced_secret: %s\n" % e)
              print("Helper:Possible chance for the partial secret update !!!")
              PROMETHEUS_METRICS['key_synced_status'].inc()
              statusFile("Fail")


class GracefulKiller:
    kill_now = False
    def __init__(self):
      signal.signal(signal.SIGINT, self.exit_gracefully)
      signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
      self.kill_now = True

# Return the UpperCase valid Key format to be updated in k8s
def stringFormatK8s(string):
    return string.replace('-', '_').upper()

# Return keys list from dictionary object
def getKeyListFromDict(dictObj):
  return list(dictObj.keys())


# Retruns the final dicionary to process Secret Modification
def getFinalDictionary(dictObj, actualNsList):
  tmp_dict = dictObj.copy()
  for key in dictObj.keys():
    if key not in actualNsList:
      tmp_dict.pop(key)
  return tmp_dict


