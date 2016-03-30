#!/bin/bash
SCRIPT_PATH=$(cd "$(dirname "$0")"; pwd)/$(basename $0)
SCRIPT_DIR=`dirname $SCRIPT_PATH`
SCRIPT_FILE=`basename $SCRIPT_PATH`

export PYTHONPATH=${SCRIPT_DIR}:${PYTHONPATH}

# python "${SCRIPT_DIR}/manage.py" syncdb
python $@
