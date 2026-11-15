#!/bin/bash
sed -i 's/^#MAKEFLAGS="-j2"/MAKEFLAGS="-j$(nproc --ignore=2)"/' /etc/makepkg.conf
sudo -u builduser python3 -m aur_builder --force-upload --owner Homelab_Infra_Prod --token $GITEA_TOKEN
