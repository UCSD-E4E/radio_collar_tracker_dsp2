#!/bin/bash
add-apt-repository ppa:up-division/5.4-upboard
apt update
apt-get autoremove -y --purge 'linux-.*generic'
apt-get install -y linux-generic-hwe-18.04-5.4-upboard
apt dist-upgrade -y
echo GRUB_RECORDFAIL_TIMEOUT=20 >> /etc/default/grub
update-grub
