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