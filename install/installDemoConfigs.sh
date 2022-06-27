#!/bin/sh

mkdir -p /data/AutomationOne

[ -e ~/AutomationOne ] || ln -s /data/AutomationOne ~/AutomationOne

cp -vr ../DemoConfigs /data/AutomationOne/

[ -e /data/AutomationOne/config.yaml ]  || ln -s /data/AutomationOne/DemoConfigs/DemoConfig.yaml /data/AutomationOne/config.yaml

