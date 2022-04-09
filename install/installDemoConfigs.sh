#!/bin/sh


[ -d ~/AutomationOne ] || mkdir ~/AutomationOne

cp -vr ../DemoConfigs ~/AutomationOne/

[ -e ~/AutomationOne/config.yaml ]  || ln -s ~/AutomationOne/DemoConfigs/DemoConfig.yaml ~/AutomationOne/config.yaml

