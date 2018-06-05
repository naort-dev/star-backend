#!/usr/bin/env bash

docker build -f dockerfiles/base-os .. --tag starsona-base-os
docker build -f dockerfiles/starsona .. --tag starsona
