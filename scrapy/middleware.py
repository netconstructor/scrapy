from collections import defaultdict

from scrapy import log
from scrapy.exceptions import NotConfigured
from scrapy.utils.misc import load_object
from scrapy.utils.defer import process_parallel, process_chain, process_chain_both

class MiddlewareManager(object):
    """Base class for implementing middleware managers"""

    component_name = 'foo middleware'

    def __init__(self, *middlewares):
        self.middlewares = middlewares
        self.methods = defaultdict(list)
        for mw in middlewares:
            self._add_middleware(mw)

    @classmethod
    def _get_mwlist_from_settings(cls, settings):
        raise NotImplementedError

    @classmethod
    def from_settings(cls, settings):
        mwlist = cls._get_mwlist_from_settings(settings)
        middlewares = []
        for clspath in mwlist:
            try:
                mwcls = load_object(clspath)
                if hasattr(mwcls, 'from_settings'):
                    mw = mwcls.from_settings(settings)
                else:
                    mw = mwcls()
                middlewares.append(mw)
            except NotConfigured, e:
                if e.args:
                    clsname = clspath.split('.')[-1]
                    log.msg("Disabled %s: %s" % (clsname, e.args[0]), log.WARNING)
        enabled = [x.__class__.__name__ for x in middlewares]
        log.msg("Enabled %ss: %s" % (cls.component_name, ", ".join(enabled)), \
            level=log.DEBUG)
        return cls(*middlewares)

    def _add_middleware(self, mw):
        if hasattr(mw, 'open_spider'):
            self.methods['open_spider'].append(mw.open_spider)
        if hasattr(mw, 'close_spider'):
            self.methods['close_spider'].insert(0, mw.close_spider)

    def _process_parallel(self, methodname, obj, *args):
        return process_parallel(self.methods[methodname], obj, *args)

    def _process_chain(self, methodname, obj, *args):
        return process_chain(self.methods[methodname], obj, *args)

    def _process_chain_both(self, cb_methodname, eb_methodname, obj, *args):
        return process_chain_both(self.methods[cb_methodname], \
            self.methods[eb_methodname], obj, *args)

    def open_spider(self, spider):
        return self._process_parallel('open_spider', spider)

    def close_spider(self, spider):
        return self._process_parallel('close_spider', spider)
