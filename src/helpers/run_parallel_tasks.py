from concurrent.futures import ProcessPoolExecutor
from src.helpers.status_file import statusFile

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