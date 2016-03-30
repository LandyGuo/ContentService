#!/bin/bash
#
# Content Web Service uWSGI Web Server init script
#
### BEGIN INIT INFO
# Provides:          contentservice
# Required-Start:    $remote_fs $remote_fs $network $syslog
# Required-Stop:     $remote_fs $remote_fs $network $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start Content Web Service uWSGI Web Server at boot time
# Description:       Content Web Service uWSGI Web Server provides web server backend.
### END INIT INFO

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/var/app/enabled/contentservice
DAEMON=`which uwsgi`
NAME=contentservice
DESC="Content Web Service uWSGI Web Server"
PROJECT=contentservice
APP_DIR=/var/app/enabled/$PROJECT
LOG_DIR=/var/app/log/$PROJECT
PID_FILE=/var/run/$NAME-uwsgi.pid


if [ -f /etc/default/$NAME ]; then
	. /etc/default/$NAME
fi

test -x $DAEMON || exit 0

set -e

function is_alive()
{
	PID=$1
	PSTATE=`ps -p "$PID" -o s=`
	if [ "D" = "$PSTATE" -o "R" = "$PSTATE" -o "S" = "$PSTATE" ]; then
		# Process is alive
		echo 'A'
	else
		# Process is dead
		echo 'D'
	fi
}

function stop_uwsgi()
{
	if [ -f "${PID_FILE}" ]; then
	    PID=`cat $PID_FILE`
	    if [ 'A' = "`is_alive $PID`" ]; then
			kill -INT $PID
		fi
		rm "$PID_FILE"
	fi
	echo "${NAME} stop/waiting."
}

function start_uwsgi()
{
	if [ -f "$PID_FILE" ]; then
		PID=`cat $PID_FILE`
		if [ 'A' = "`is_alive $PID`" ]; then
			echo "$NAME is already running."
		else
	    	rm "$PID_FILE"
			start_uwsgi
		fi
	else
	    pushd "$APP_DIR" >/dev/null
		uwsgi -x uwsgi.xml --pidfile="$PID_FILE"
	    popd >/dev/null
	fi
}


case "$1" in
	start)
		echo -n "Starting $DESC..."
		start_uwsgi
		echo "Done."
		;;
	stop)
		echo -n "Stopping $DESC..."
		stop_uwsgi
		echo "Done."
		;;
	restart)
		echo -n "Restarting $DESC..."
		stop_uwsgi
		sleep 6
		start_uwsgi
		echo "Done."
		;;


	status)
		status_of_proc -p $PID_FILE "$DAEMON" uwsgi && exit 0 || exit $?
		;;
	*)
		echo "Usage: $NAME {start|stop|restart|status|upload}" >&2
		exit 1
		;;
esac

exit 0
