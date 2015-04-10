#!/bin/sh
set -e

NAME=encryption-milter
DAEMON=/usr/sbin/$NAME
PIDFILE=/home/encmilter/$NAME.pid
KEYRING=/home/encmilter/mailkeyring.pub
SOCKET="inet:1337@127.0.0.1"
USER=encmilter
OPTIONS="--pidfile $PIDFILE --socket $SOCKET --keyring $KEYRING"
export PATH="${PATH:+$PATH:}/usr/sbin:/sbin"

case "$1" in
  start)
        echo -n "Starting daemon: "$NAME
        start-stop-daemon --chuid $USER --start --background --quiet --oknodo --pidfile $PIDFILE --exec $DAEMON -- $OPTIONS
        echo "..."
        ;;
  stop)
        echo -n "Stopping daemon: "$NAME
        start-stop-daemon --stop --quiet --oknodo --pidfile $PIDFILE
        rm -f $PIDFILE
        echo "..."
        ;;
  restart)
        echo -n "Restarting daemon: "$NAME
        start-stop-daemon --stop --quiet --oknodo --retry 30 --pidfile $PIDFILE
        start-stop-daemon --chuid $USER --start --background --quiet --oknodo --pidfile $PIDFILE --exec $DAEMON -- $OPTIONS
        echo "..."
        ;;
  *)
        echo "Usage: "$1" {start|stop|restart}"
        exit 1
esac

exit 0
