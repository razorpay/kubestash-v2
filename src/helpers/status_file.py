
# Status Healthy/Fail
def statusFile(code="Healthy"):
  with open('./prom/status', 'w') as fp:
    fp.write(code)