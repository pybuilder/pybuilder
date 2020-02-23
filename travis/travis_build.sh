#!/bin/bash

source ~/.bash_profile
pyenv activate pyb-$PYTHON_VERSION

set -eu

DEPLOY_VERSION=""
DEPLOY_BRANCH=""
if [ "$TRAVIS_PULL_REQUEST" = "false" ]; then
    echo "Running Production Build"
    for v in $DEPLOY_PYTHONS; do
        if [ "$TRAVIS_PYTHON_VERSION" = "$v" ]; then
            DEPLOY_VERSION=1
            break
        fi
    done

    for b in $DEPLOY_BRANCHES; do
        if [ "$TRAVIS_BRANCH" = "$b" ]; then
            DEPLOY_BRANCH=1
            break
        fi
    done

    if [ "$DEPLOY_BRANCH$DEPLOY_VERSION" = "11" ]; then
        echo "This build will be deployed!"
        PYB_ARGS="$PYB_ARGS upload"
    fi
else
    echo "Running PR Build"
fi

./build.py $PYB_ARGS
