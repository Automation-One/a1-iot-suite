

import logging
import random


logger = logging.getLogger("AutomationOne")


# Functions for config00.yaml

def getRand(node):
    """Callback function for getting a random number"""
    node.setValue(random.random())


def add_Nodes(values):
    """Callback function for adding the values of multiple nodes"""
    return sum(values);


def log_value(node):
    logger.info("[{}] {}".format(node.name,node.getValue()))