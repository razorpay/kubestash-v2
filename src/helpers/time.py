# Return Current UTC time in IST Format
def getcurrentISTtime():
  IST = pytz.timezone('Asia/Kolkata')
  now = datetime.now(IST)
  ist_string = now.strftime("%d/%b/%Y %H:%M:%S IST")
  return ist_string