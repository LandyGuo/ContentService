#!/bin/bash
#
# This scripts is used to install dependencies for the application.

#Install mongodb
#http://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/

SYS_DEPS=(build-essential python-pip python-dev m2crypto libxml2-dev libxslt-dev cmake python-qt4)
#Enable Mongo Textsearch: db.adminCommand({setParameter : 1, textSearchEnabled : true})

PYTHON_DEPS=(django uwsgi pymongo requests amqp scrapy urllib3 ghost.py)

function install_dependencies()
{
   # update to latest to avoid some packages can not found.
   aptitude update
   echo "Installing required system packages..."
   for sys_dep in ${SYS_DEPS[@]};do
       install_sys_dep $sys_dep
   done
   echo "Installing required system packages finished."

   echo "Installing required python packages..."
   for python_dep in ${PYTHON_DEPS[@]};do
       install_python_dep ${python_dep}
   done
   echo "Installing required python packages finished."

}


function install_sys_dep()
{
    # input args  $1 package name
    if [ `aptitude  search  $1  | grep -c "^i \+${1} \+"` = 0 ];then
        aptitude -y install  $1
    else
        echo "Package ${1} already installed."
    fi
}

function install_python_dep()
{
    # input args $1 like simplejson==1.0 ,can only extractly match
    if [ `pip freeze | grep -c "${1}"` = 0 ];then
        pip install  $1
    else
        echo "Python package ${1} already installed."
    fi
}
install_dependencies
