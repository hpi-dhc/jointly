import logging

FORMAT = "[%(lineno)3s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('jointly')
logger.setLevel(logging.CRITICAL)