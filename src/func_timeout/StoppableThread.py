import os
import ctypes
import threading

class StoppableThread(threading.Thread):

    def _stopThread(self, exception, raiseEvery=2.0):
        if self.is_alive() is False:
            return True

        self._stderr = open(os.devnull, 'w')
        joinThread = JoinThread(self, exception, repeatEvery=raiseEvery)
        joinThread._stderr = self._stderr
        joinThread.start()
        joinThread._stderr = self._stderr


    def stop(self, exception, raiseEvery=2.0):
        return self._stopThread(exception, raiseEvery)


class JoinThread(threading.Thread):
    def __init__(self, otherThread, exception, repeatEvery=2.0):
        threading.Thread.__init__(self)
        self.otherThread = otherThread
        self.exception = exception
        self.repeatEvery = repeatEvery
        self.daemon = True

    def run(self):
        self.otherThread._Thread__stderr = self._stderr
        if hasattr(self.otherThread, '_Thread__stop'):
            self.otherThread._Thread__stop()
        while self.otherThread.is_alive():
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.otherThread.ident), ctypes.py_object(self.exception))
            self.otherThread.join(self.repeatEvery)
        try:
            self._stderr.close()
        except:
            pass
