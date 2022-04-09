#!/bin/sh

cp ../AutomationOne.py /usr/bin/AutomationOne
chmod a+x /usr/bin/AutomationOne

cp ../AutomationOne.service /lib/systemd/system/AutomationOne.service