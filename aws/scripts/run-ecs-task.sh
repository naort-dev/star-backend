#!/usr/bin/env bash
set -e

stack_output=$(mktemp)
aws cloudformation describe-stacks --stack-name $1 > $stack_output

CLUSTER=`jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "ClusterName").OutputValue' $stack_output`
SUBNET1=`jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "PrivateSubnetOne").OutputValue' $stack_output`
SUBNET2=`jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "PrivateSubnetTwo").OutputValue' $stack_output`
SECURITY_GROUP=`jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "FargateContainerSecurityGroup").OutputValue' $stack_output`
rm $stack_output

run_task_output=$(mktemp)
aws ecs run-task --cluster $CLUSTER \
    --task-definition $2-backend-app-$3 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
    > $run_task_output

TASK_ID=`jq -r '.tasks[0].taskArn' $run_task_output | cut -d/ -f2`
aws ecs wait tasks-stopped --cluster $CLUSTER --tasks $TASK_ID

EXIT_CODE=`aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ID | jq -r '.tasks[0].containers[0].exitCode'`
rm $run_task_output

aws logs get-log-events --log-group-name $2-backend-app --log-stream-name backend/$3/$TASK_ID | jq -r .events[].message

exit $EXIT_CODE