#!/bin/bash
SCRIPTPATH=`dirname $0`

aws cloudformation update-stack --stack-name backend-$1 --template-body file://./$SCRIPTPATH/$1.yml
