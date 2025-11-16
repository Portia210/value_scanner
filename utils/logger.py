import logging

_logger = None

def get_logger():
    global _logger
    if _logger is None:
        _logger = logging.getLogger("main_logger")
        _logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - {%(filename)s:%(lineno)d} - %(levelname)s - %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        _logger.addHandler(ch)
        _logger.propagate = False
    return _logger