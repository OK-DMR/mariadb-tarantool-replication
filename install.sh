#!/bin/bash

PREFIX="/opt/MariaDBReplica"
BINARY="replica.py"
USER="replica"
GROUP="replica"
SYSTEMD_UNIT="replicatord.service"
SETTINGS_FILE="replica.yml"

# Prepare prefix and install necessary files
mkdir -p ${PREFIX}
cp ${BINARY} ${PREFIX}
if [ ! -d $PREFIX/${SETTINGS_FILE} ]
then
  cp 'replica.default.yml' ${PREFIX}/${SETTINGS_FILE}
fi
chmod +x ${PREFIX}/${BINARY}

# Setup user/group to contain the service
useradd -U ${USER}
chown -R ${USER}:${GROUP} ${PREFIX}
chmod +x ${PREFIX}

cp -f ${SYSTEMD_UNIT} /lib/systemd/system/
systemctl daemon-reload
systemctl start systemd-modules-load
