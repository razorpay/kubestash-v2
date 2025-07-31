from prometheus_client import CollectorRegistry, multiprocess, start_http_server
from secret_fetcher.dynamodb.ddbmonitor import init_ddbwatch
from helpers.status_file import statusFile
from helpers.run_parallel_tasks import run_cpu_tasks_in_parallel
from flaskServer import initFlaskServer


if __name__ == "__main__":
  try:
    print("Main:Started listening the change in Secrets...")
    statusFile()
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    start_http_server(8000, registry=registry)
    print("Main:Listing to sync the secrets as well!!!")
    run_cpu_tasks_in_parallel([
        init_ddbwatch,
        initFlaskServer,
    ])
  except Exception as e:
    print("Main:Exception in listening changes in DDB/Bigtable. %s\n" % e)
    statusFile("Fail")
