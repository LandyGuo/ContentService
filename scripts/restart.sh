#!/bin/sh

service contentcrawler stop
sleep 2
service contentcrawler start

service contentservice stop
sleep 2
service contentservice start
