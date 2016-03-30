#!/bin/bash
#
# This scripts is used to install the application.
# This scripts is required for all projects.
#
#
# Author : chzhong
#
SCRIPT_DIR=`dirname $0`

if [ "$1" = "checkdeps" ] ; then
    echo "Checking and installing dependecies..."
    if [ -f "${SCRIPT_DIR}/install_deps.sh" ]; then
        ${SCRIPT_DIR}/install_deps.sh
    else
        echo "Depedency install script not found."
    fi
fi

PROJECT=contentservice

PTH_FILE='contentservice.pth'
if [ "$2" = "lib" ] ; then
    sudo python setup.py -q install
else
    pwd > ${PTH_FILE}
    sudo python scripts/install.py
fi

echo Installing service...
[ -z `grep "^$USER:" /etc/passwd` ] && sudo useradd -r $USER -M -N

PROJECT_DIR="/var/app/enabled/$PROJECT"

chmod -R a+rw /var/app/data/$PROJECT
chmod -R a+rw /var/app/log/$PROJECT
chown $USER:nogroup /var/app/data/$PROJECT
chown $USER:nogroup /var/app/log/$PROJECT

ln -sf /var/app/enabled/$PROJECT/scripts/contentservice-init.sh /etc/init.d/contentservice
ln -sf /var/app/enabled/$PROJECT/scripts/contentcrawler-init.sh /etc/init.d/contentcrawler

find /var/app/enabled/$PROJECT/scripts/init/ -iname '*.conf' -exec cp {} /etc/init/ \;

update-rc.d $PROJECT defaults

echo Configuring ${PROJECT}...
if [ -f "$PROJECT.cron" ] ; then
    cp $PROJECT_DIR/$PROJECT.cron /etc/cron.d/$PROJECT
fi

if [ -f "$PROJECT.logrotate" ] ; then
    ln -sf $PROJECT_DIR/$PROJECT.logrotate /etc/logrotate.d/$PROJECT
fi
