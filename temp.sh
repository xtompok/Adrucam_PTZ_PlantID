#!/bin/sh

sudo mount -t ramfs -o size=2g ramfs /tmp/ram
sudo chown jethro:jethro /tmp/ram
