#!/bin/sh

cp -v ../AutomationOne.py /usr/bin/AutomationOne
chmod a+x /usr/bin/AutomationOne

cp -v ../AutomationOne.service /lib/systemd/system/AutomationOne.service