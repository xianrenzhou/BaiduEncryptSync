#!/bin/bash
set -e

# 准备命令行参数
ARGS="-d ${WATCH_DIR} -r ${REMOTE_DIR} -c ${COOLDOWN} -s ${MIN_SIZE}"

# 根据环境变量添加其他参数
if [ "$ENCRYPT" = "true" ]; then
    ARGS="$ARGS -e -p ${PASSWORD}"
fi

if [ "$RECURSIVE" = "false" ]; then
    ARGS="$ARGS -n"
fi

if [ "$UPLOAD_EXISTING" = "true" ]; then
    ARGS="$ARGS -u"
fi

if [ ! -z "$FILE_TYPES" ]; then
    ARGS="$ARGS -t ${FILE_TYPES}"
fi

if [ ! -z "$EXCLUDE" ]; then
    ARGS="$ARGS -x ${EXCLUDE}"
fi

if [ ! -z "$EXCLUDE_DIRS" ]; then
    ARGS="$ARGS -X ${EXCLUDE_DIRS}"
fi

if [ ! -z "$WORKERS" ]; then
    ARGS="$ARGS -w ${WORKERS}"
fi

if [ ! -z "$AUTH_CODE" ]; then
    ARGS="$ARGS --auth-code ${AUTH_CODE}"
fi

# 运行应用
echo "Starting BaiduEncryptSync with arguments: $ARGS"
python main.py $ARGS

# 如果用户需要自定义命令，则执行它们
exec "$@"
