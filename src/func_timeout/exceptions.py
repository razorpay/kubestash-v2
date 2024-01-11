RETRY_SAME_TIMEOUT = 'RETRY_SAME_TIMEOUT'

class FunctionTimedOut(BaseException):

    def __init__(self, msg='', timedOutAfter=None, timedOutFunction=None, timedOutArgs=None, timedOutKwargs=None):
        self.timedOutAfter = timedOutAfter

        self.timedOutFunction = timedOutFunction
        self.timedOutArgs = timedOutArgs
        self.timedOutKwargs = timedOutKwargs
        if not msg:
            msg = self.getMsg()

        BaseException.__init__(self, msg)
        self.msg = msg


    def getMsg(self):
        if self.timedOutFunction is not None:
            timedOutFuncName = self.timedOutFunction.__name__
        else:
            timedOutFuncName = 'Unknown Function'
        if self.timedOutAfter is not None:
            timedOutAfterStr = f"{self.timedOutAfter:f}"
        else:
            timedOutAfterStr = "Unknown"
        return f'Function {timedOutFuncName} (args={repr(self.timedOutArgs)}) (kwargs={repr(self.timedOutKwargs)}) timed out after {timedOutAfterStr} seconds.\n'

    
    def retry(self, timeout=RETRY_SAME_TIMEOUT):
        if timeout is None:
            return self.timedOutFunction(*(self.timedOutArgs), **self.timedOutKwargs)
        from .dafunc import func_timeout
        if timeout == RETRY_SAME_TIMEOUT:
            timeout = self.timedOutAfter
        return func_timeout(timeout, self.timedOutFunction, args=self.timedOutArgs, kwargs=self.timedOutKwargs)

