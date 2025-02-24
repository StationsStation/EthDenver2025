#! /usr/bin/env bash

# This script is used to run the pre-commit checks for the repository.
# It is called by the pre-commit hook in the repository.


function check_output_command() {
    if [ $? -ne 0 ]; then
        echo "Error: $1"
        exit 1
    fi
}

function process() {
    poetry run adev -n 0 -v fmt -co 
    check_output_command "Error in formatting the code"
    poetry run adev -n 0 -v lint -co
    check_output_command "Error in linting the code"
}

process
