#!/usr/bin/python3

import logging
import logging.handlers
import logging.config
import sys

from AutomationOne import Handler

logger = logging.getLogger("AutomationOne")
logger.setLevel(logging.DEBUG)

streamHandler = logging.StreamHandler()
streamHandler.setLevel(logging.INFO)
streamFormatter = logging.Formatter('[%(levelname)s]  %(message)s')
streamHandler.setFormatter(streamFormatter)
logger.addHandler(streamHandler)



def main():
    configFile = "config.yaml"
    if len(sys.argv) > 1:
        configFile = sys.argv[1]

    handler = Handler()
    handler.parseConfig(configFile)
    handler.run()

if __name__ == "__main__":
    main()






