import logging
from time import time
from django.http import HttpRequest

pref_logger = logging.getLogger('perf')

def perf_logged(logger = pref_logger, log_retvalue = False):
    """
    Record the performance of each method call.
    """
    def decorator(func):
        def inner(*args, **kwargs):
            argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
            fname = func.func_name
            if len(args) >= 1 and isinstance(args[0], HttpRequest):
                req = args[0]
                call = '%s %s %s -> %s(%s)' % (req.META['REMOTE_ADDR'], req.method, req.META['PATH_INFO'], fname, ','.join('%s=%s' % entry for entry in zip(argnames[1:], args[1:]) + kwargs.items() + req.GET.items()))
            else:
                call = '%s(%s)' % (fname, ','.join('%s=%s' % entry for entry in zip(argnames, args) + kwargs.items()))
            ret = None
            try:
                startTime = time()
                ret = func(*args, **kwargs)
                return ret
            finally:
                endTime = time()
                logger.debug('%s\t%s\t%s ms.' % (call, ret if log_retvalue else "", 1000 * (endTime - startTime)))
        return inner
    return decorator