#!/bin/sh
set -ex

if [ "$#" -ge 1 ]; then
  branch="$1"
else
  branch="master"
fi

tmpdir=$(mktemp -d)

cd $tmpdir

wget "https://github.com/Automation-One/a1-iot-suite/archive/refs/heads/$branch.zip"
unzip $branch.zip > /dev/null

install_path="$tmpdir/a1-iot-suite-$branch/install/"

cd $install_path
/bin/sh installModbus.sh
cd $install_path
/bin/sh installAutomationOne.sh
cd $install_path
/bin/sh installDemoConfigs.sh

cd /
rm -r $tmpdir
