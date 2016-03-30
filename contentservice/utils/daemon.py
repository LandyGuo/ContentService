'''
    ***
    Modified generic daemon class
    ***

    Author:     http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
                www.boxedice.com

    License:    http://creativecommons.org/licenses/by-sa/3.0/

    Changes:    23rd Jan 2009 (David Mytton <david@boxedice.com>)
                - Replaced hard coded '/dev/null in __init__ with os.devnull
                - Added OS check to conditionally remove code that doesn't work on OS X
                - Added output to console on completion
                - Tidied up formatting
                11th Mar 2009 (David Mytton <david@boxedice.com>)
                - Fixed problem with daemon exiting on Python 2.4 (before SystemExit was part of the Exception base)
                13th Aug 2010 (David Mytton <david@boxedice.com>
                - Fixed unhandled exception if PID file is empty
'''

# Core modules
import atexit
import os
import sys
import time

from signal import SIGTERM

class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, logfile=None, name=None, uid=None, gid=None, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull):
        self.name = name
        self.uid = uid
        self.gid = gid
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def change_proc_name(self):
        """
        Change the name of the process.
        """
        try:
            from setproctitle import setproctitle
            setproctitle(self.name)
        except ImportError:
            pass

    def daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # Exit first parent
                sys.exit(0)
            self.change_proc_name()
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Write pidfile
        atexit.register(self.delpid) # Make sure pid file is removed if we quit
        file(self.pidfile, 'w+').write("%s\n" % os.getpid())

    def delpid(self):
        try:
            pid = open(self.pidfile).read().strip()
            if pid == str(os.getpid()):
                os.remove(self.pidfile)
        except:
            pass

    @property
    def pid(self):
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except SystemExit:
            pid = None
        return pid

    @property
    def current_status(self):
        """
        Status of the daemon.
        """
        pid = self.pid
        running = True if pid else False
        return running

    def status(self):
        """
        Status of the daemon.
        """
        pid = self.pid
        running = True if pid else False
        if running:
            print '%s start/running, process %s' % (self.name, pid)
        else:
            print '%s stopped/waiting.' % (self.name,)
        return running

    def guard(self):
        pid = self.pid
        if pid:
            import psutil
            proc = psutil.Process(pid)
            status = proc.status
            print '%s %s, process %s' % (self.name, status, pid)
            if status in (psutil.STATUS_DEAD, psutil.STATUS_STOPPED, psutil.STATUS_ZOMBIE):
                self.logger.warn('%s is in status of %s, restarting...', self.name, status)
                try:
                    self.stop()
                    self.start()
                except Exception, e:
                    self.logger.exception('Failed to restart %s.', self.name)
                    print e
            elif status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                self.logger.info('%s is still running.', self.name)
            else:
                self.logger.info('%s is in unknown status %s.', self.name, status)
        else:
            self.logger.info('%s stopped manually.', self.name)

    def start(self):
        """
        Start the daemon
        """
        pid = self.pid

        if pid:
            message = "pidfile %s already exists. Is it already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        pid = self.pid

        if not pid:
            message = "pidfile %s does not exist. Not running?\n"
            sys.stderr.write(message % self.pidfile)

            # Just to be sure. A ValueError might occur if the PID file is empty but does actually exist
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)

            return # Not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
            print '%s stopped/waiting.' % (self.name,)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        raise NotImplemented()
