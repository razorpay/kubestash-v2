import signal
from src.helpers.status_file import statusFile
from src.env import NAMESPACE_EXCLUDE_FILTER


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


