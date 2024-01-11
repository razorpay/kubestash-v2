from prometheus_client import CollectorRegistry, multiprocess, start_http_server
from ddbmonitor import init_ddbwatch
from helpers import statusFile, run_cpu_tasks_in_parallel 
from flaskServer import initFlaskServer


if __name__ == "__main__":
  try:
    print("Main:Started listning the change in Secrets...")
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
    print("Main:Exception in listning changes in DDB. %s\n" % e)
    statusFile("Fail")
