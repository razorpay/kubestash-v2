from prometheus_client import Counter, Gauge, Summary

from env import *


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