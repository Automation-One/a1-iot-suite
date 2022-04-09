#!/bin/sh


[ -d ~/AutomationOne ] || mkdir ~/AutomationOne

cp -r ../DemoConfigs ~/AutomationOne/DemoConfigs

[ -f ~/AutomationOne/config.yaml ]  || ln -s ~/AutomationOne/DemoConfigs/DemoConfig.yaml ~/AutomationOne/config.yaml

