#!/bin/bash
echo 'Start crysadm on'  $(date) >> /tmp/crysadm.txt

sudo pkill redis-server
sudo pkill python3.4

BASE_DIR="$( cd "$( dirname "$0"  )" && pwd  )"                                                             
ls ${BASE_DIR}/ >> /tmp/error 2>&1
                                     
echo $PATH >> /tmp/error           
echo $LD_LIBRARY_PATH >> /tmp/error                                            
sudo /etc/init.d/redis-server restart
sudo redis-server >> /tmp/error 2>&1 &                                              
sudo python3.4 ${BASE_DIR}/crysadm/crysadm_helper.py >> /tmp/error 2>&1 &
sudo python3.4 ${BASE_DIR}/crysadm/crysadm.py >> /tmp/error 2>&1 & 
