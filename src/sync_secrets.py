import func_timeout
from func_timeout.exceptions import FunctionTimedOut
from helpers import CLUSTER_NAME, CREDSTASH_SYNC_TIMEOUT_SECS, UPDATING_SECRETS, addUpdateK8sSecret, describe_all_ns, getActualNSList, getFinalDictionary, getKeyListFromDict, parseExcludeNsFilter, statusFile
from secret_fetcher.factory import get_secret_fetcher
from metrics.prometheus_metrics import PROMETHEUS_METRICS


def syncSecretFromSource(updating_secrets=UPDATING_SECRETS):
    print(f"Helper:Starting the syncing of Secrets in {CLUSTER_NAME} cluster...")
    
    fetcher = get_secret_fetcher()
    
    try:
        secrets_data = func_timeout(CREDSTASH_SYNC_TIMEOUT_SECS, fetcher.fetch_secrets)
    except FunctionTimedOut:
        print(f"Helper:Timeout of {CREDSTASH_SYNC_TIMEOUT_SECS} secs while fetching secrets.")
        statusFile("Fail")
        PROMETHEUS_METRICS['table_fetch_status'].inc()
        raise
    
    # Proceed with your existing Kubernetes sync logic
    ns_in_k8s = describe_all_ns()
    exclude_ns_list = parseExcludeNsFilter()
    actual_ns_list = getActualNSList(getKeyListFromDict(secrets_data), ns_in_k8s, exclude_ns_list)
    
    final_dict_to_process = getFinalDictionary(secrets_data, actual_ns_list)
    addUpdateK8sSecret(final_dict_to_process)
    
    print("Helper:Completed the syncing of Secrets.")
