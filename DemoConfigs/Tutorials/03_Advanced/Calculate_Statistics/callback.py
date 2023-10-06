

import logging
import random



logger = logging.getLogger("AutomationOne")


# Functions for config00.yaml

def getRand(node):
    """Callback function for getting a random number"""

    node.setValue(random.random())


def calculate_statistics(value,count,token):
    """Callback function for calculating the minimum, maximum and average values over a specified time span"""
    if not token in calculate_statistics.values.keys():
        calculate_statistics.values[token] = []
    calculate_statistics.values[token].append(value[0]) # We get the values in form of [value] therefore we have to unpack it first.
    n = len(calculate_statistics.values[token])
    if n < count:
        return None
    minimum = min(calculate_statistics.values[token])
    maximum = max(calculate_statistics.values[token])
    total = sum(calculate_statistics.values[token])
    average = total/n
    calculate_statistics.values[token] = []
    return [minimum, maximum, total, average]
calculate_statistics.values = {}



def log_value(node):
    logger.info("[{}] {}".format(node.name,node.getValue()))