#!/bin/sh

cp -v -R ../AutomationOne /usr/lib/python3.8/site-packages

cp -v ../AutomationOne.py /usr/bin/AutomationOne
chmod a+x /usr/bin/AutomationOne

cp -v ../AutomationOne.service /lib/systemd/system/AutomationOne.service