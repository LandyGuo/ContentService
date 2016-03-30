#!/bin/bash

PROJECT=contentservice
NAME=contentservice
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/var/app/enabled/$PROJECT
DESC="Content Crawler Service"
APP_DIR=/var/app/enabled/$PROJECT
LOG_DIR=/var/app/log/$PROJECT
MANAGE=$APP_DIR/manage.py

if [ -f /etc/default/$NAME ]; then
	. /etc/default/$NAME
fi

test -f $MANAGE || exit 0

set -e


case "$1" in
	start)
		echo -n "Starting $DESC..."
		python $MANAGE runscript crawlerservice start  > /dev/null 2>&1
		echo "Done."
		;;
	stop)
		echo -n "Stopping $DESC..."
		python $MANAGE runscript crawlerservice stop
		echo "Done."
		;;
	restart)
		echo -n "Restarting $DESC..."
		python $MANAGE runscript crawlerservice restart
		echo "Done."
		;;

	status)
		python $MANAGE runscript crawlerservice status
		;;
	*)
		echo "Usage: $NAME {start|stop|restart|status}" >&2
		exit 1
		;;
esac

exit 0
