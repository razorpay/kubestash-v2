import copy
import types
import sys

from .exceptions import FunctionTimedOut
from .StoppableThread import StoppableThread

from functools import wraps

__all__ = ('func_timeout', 'func_set_timeout')


def raise_exception(exception):
    raise exception[0] from None


def func_timeout(timeout, func, args=(), kwargs=None):
    if not kwargs:
        kwargs = {}
    if not args:
        args = ()
    ret = []
    exception = []
    isStopped = False
    def funcwrap(args2, kwargs2):
        try:
            ret.append( func(*args2, **kwargs2) )
        except FunctionTimedOut:
            # Don't print traceback to stderr if we time out
            pass
        except Exception as e:
            exc_info = sys.exc_info()
            if isStopped is False:
                e.__traceback__ = exc_info[2].tb_next
                exception.append(e)

    thread = StoppableThread(target=funcwrap, args=(args, kwargs))
    thread.daemon = True

    thread.start()
    thread.join(timeout)

    stopException = None
    if thread.is_alive():
        isStopped = True

        class FunctionTimedOutTempType(FunctionTimedOut):
            def __init__(self):
                return FunctionTimedOut.__init__(self, '', timeout, func, args, kwargs)

        FunctionTimedOutTemp = type('FunctionTimedOut' + str( hash( "%d_%d_%d_%d" %(id(timeout), id(func), id(args), id(kwargs))) ), FunctionTimedOutTempType.__bases__, dict(FunctionTimedOutTempType.__dict__))

        stopException = FunctionTimedOutTemp
        thread._stopThread(stopException)
        thread.join(min(.1, timeout / 50.0))
        raise FunctionTimedOut('', timeout, func, args, kwargs)
    else:
        thread.join(.5)
    if exception:
        raise_exception(exception)
    if ret:
        return ret[0]


def func_set_timeout(timeout, allowOverride=False):
    defaultTimeout = copy.copy(timeout)
    isTimeoutAFunction = bool(issubclass(timeout.__class__, (types.FunctionType,
        types.MethodType, types.LambdaType, types.BuiltinFunctionType, types.BuiltinMethodType)))

    if not isTimeoutAFunction:
        if not issubclass(timeout.__class__, (float, int)):
            try:
                timeout = float(timeout)
            except:
                raise ValueError(f'timeout argument must be a float/int for number of seconds, or a function/lambda which gets passed the function arguments and returns a calculated timeout (as float or int). Passed type: < {timeout.__class__.__name__} > is not of any of these, and cannot be converted to a float.')


    if not allowOverride and not isTimeoutAFunction:
        def _function_decorator(func):
            return wraps(func)(lambda *args, **kwargs : func_timeout(defaultTimeout, func, args=args, kwargs=kwargs))
        return _function_decorator

    if not isTimeoutAFunction:
        def _function_decorator(func):
            def _function_wrapper(*args, **kwargs):
                if 'forceTimeout' in kwargs:
                    useTimeout = kwargs.pop('forceTimeout')
                else:
                    useTimeout = defaultTimeout

                return func_timeout(useTimeout, func, args=args, kwargs=kwargs)

            return wraps(func)(_function_wrapper)
        return _function_decorator

    timeoutFunction = timeout

    if allowOverride:
        def _function_decorator(func):
            def _function_wrapper(*args, **kwargs):
                if 'forceTimeout' in kwargs:
                    useTimeout = kwargs.pop('forceTimeout')
                else:
                    useTimeout = timeoutFunction(*args, **kwargs)

                return func_timeout(useTimeout, func, args=args, kwargs=kwargs)

            return wraps(func)(_function_wrapper)
        return _function_decorator

    def _function_decorator(func):
        def _function_wrapper(*args, **kwargs):
            useTimeout = timeoutFunction(*args, **kwargs)

            return func_timeout(useTimeout, func, args=args, kwargs=kwargs)

        return wraps(func)(_function_wrapper)
    return _function_decorator

