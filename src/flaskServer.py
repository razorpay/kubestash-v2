from flask import Flask, abort, request
from waitress import serve
from helpers.status_file import statusFile
from env import FLASK_API_KEY, VERBOSE
from metrics.prometheus_metrics import PROMETHEUS_METRICS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging


logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger("urllib3").propagate = False
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)


# Rate limit handler for sync api
def ratelimit_handler():
  if VERBOSE:
    print("Flask:Blocked.Too many requests. Allowed 1/10 mins")
  PROMETHEUS_METRICS['bad_request_count'].inc()
  return "<b>Return Code : 429</b><p>Too many requests. Allowed 1/10 mins.</p>"


# Flask server to be called
def initFlaskServer():
  @app.route("/syncnow")
  @limiter.limit("1 per 10 minute", error_message=ratelimit_handler)
  def syncnow():
    try:
      key = request.headers.get('API-Key')
      if key == FLASK_API_KEY:
        syncSecretFromDDB()
        PROMETHEUS_METRICS['valid_request_count'].inc()
        return "<b>Return Code : 200</b><p> Synced.</p>"
      else:
        PROMETHEUS_METRICS['malformed_request_count'].inc()
        return "<b>Return Code : 400</b><p> Invalid/Malformed Request.</p>", 400
    except Exception as e:
      print("Flask:Exception in syncing the secrets. %s\n" % e)
      statusFile("Fail")
      abort(500)


  @app.errorhandler(404)
  def page_not_found(error):
    if VERBOSE:
      print("{}:{} - {}".format(request.path, request.method, error))
    PROMETHEUS_METRICS['not_found_count'].inc()
    return "<b>Return Code : 404</b><p> Page not found.</p>", 404


  @app.errorhandler(500)
  def internal_error(error):
    print("%s" % error)
    PROMETHEUS_METRICS['server_error_count'].inc()
    return "<b>Return Code : 500</b><p> Refer Logs.</p>", 500

  serve(app, host="0.0.0.0", port=8080)

