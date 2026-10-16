"""Bounded local error log, initialized only if a runtime error occurs."""
_logger = None
_last = {}


def record_error(context, error):
    global _logger
    import time
    now = time.monotonic()
    if context in _last and now - _last[context] < 30:
        return
    _last[context] = now
    try:
        if _logger is None:
            import logging
            from logging.handlers import RotatingFileHandler
            from app_paths import ROOT
            folder = ROOT / 'Saved' / 'diagnostics'
            folder.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(str(folder / 'runtime.log'), maxBytes=262144,
                                          backupCount=2, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            _logger = logging.getLogger('MyServant.runtime')
            _logger.addHandler(handler)
            _logger.setLevel(logging.ERROR)
            _logger.propagate = False
        _logger.error(context, exc_info=(type(error), error, error.__traceback__))
    except OSError:
        pass
