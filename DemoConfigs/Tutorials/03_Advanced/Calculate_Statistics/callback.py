

import logging
import random



logger = logging.getLogger("AutomationOne")


# Functions for config00.yaml

def getRand(node):
    """Callback function for getting a random number"""

    node.setValue(random.random())


def calculate_statistics(value,count):
    """Callback function for calculating the minimum, maximum and average values over a specified time span"""
    calculate_statistics.values.append(value[0]) # We get the values in form of [value] therefore we have to unpack it first.
    n = len(calculate_statistics.values)
    if n < count:
        return None
    minimum = min(calculate_statistics.values)
    maximum = max(calculate_statistics.values)
    total = sum(calculate_statistics.values)
    average = total/n
    calculate_statistics.values = []
    return [minimum, maximum, total, average]
calculate_statistics.values = []



def log_value(node):
    logger.info("[{}] {}".format(node.name,node.getValue()))