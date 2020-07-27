#!/usr/bin/env bash
set -ex

## Script to be run by Wycliffe Associates Jenkins
## instance. Deploys Lambda functions via Apex, then
## updates select functions to run with the Pypy runtime
## and extra RAM.

case $JOB_NAME in

  *Master*)
    export APEX_ENV="prod"
    export FN_PREFIX=""
    ;;
    
  *Dev*)
    export APEX_ENV="develop"
    export FN_PREFIX="dev-"
    ;;
    
  *)
    echo Unknown job name.
    exit 1
    ;;
    
esac

export FN_LIST=(
  "d43-catalog_signing"
  "d43-catalog_uw_v2_catalog"
  "d43-catalog_ts_v2_catalog"
)
export LAYER="arn:aws:lambda:us-east-2:581647696645:layer:pypy27:5"
export AWS_CLI="/home/jenkins/.local/bin/aws"

export AWS_REGION="us-east-2"
export AWS_DEFAULT_REGION=$AWS_REGION

cp "$privateKey" libraries/tools/signer/uW-sk.pem
cp "$publicKey" libraries/tools/signer/uW-sk.pub
chmod a+r libraries/tools/signer/uW-sk*

chmod u+x apex
./apex deploy --env=$APEX_ENV

for fn in "${FN_LIST[@]}"; do
  $AWS_CLI lambda update-function-configuration --function-name $FN_PREFIX$fn \
    --runtime provided --layers $LAYER --memory-size 1024
done

