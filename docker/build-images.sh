#!/usr/bin/env bash

docker build -f dockerfiles/base-os .. --tag starsona-base-os
docker build -f dockerfiles/base-httpd .. --tag starsona-base-httpd
docker build -f dockerfiles/base-backend .. --tag starsona-base-backend
