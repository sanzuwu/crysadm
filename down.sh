#!/bin/sh
echo 'Stop crysadm on'  $(date) >> /tmp/crysadm.txt

sudo pkill redis-server
sudo pkill python3.4

