#!/usr/bin/env bash

set -euo pipefail

# Define versions
PROTOC_VERSION="27.2"
PROTOLINT_VERSION="0.50.0"


# Function to get the appropriate download URL based on OS and architecture
get_download_url() {
    local tool=$1
    local os=$(uname -s)
    local arch=$(uname -m)

    case "$os" in
        Linux)
            protoc_os="linux"
            protolint_os="Linux"
            ;;
        Darwin)
            protoc_os="osx"
            protolint_os="darwin"
            ;;
        *)
            echo "Unsupported OS: $os" >&2
            return 1
            ;;
    esac

    case "$arch" in
        x86_64)
            protoc_arch="x86_64"
            protolint_arch="amd64"
            ;;
        arm64|aarch64)
            protoc_arch="aarch_64"
            protolint_arch="arm64"
            ;;
        *)
            echo "Unsupported architecture: $arch" >&2
            return 1
            ;;
    esac

    if [ "$tool" = "protoc" ]; then
        if [ "$os" = "Darwin" ]; then
            echo "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-osx-universal_binary.zip"
        else
            echo "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-${protoc_os}-${protoc_arch}.zip"
        fi
    elif [ "$tool" = "protolint" ]; then
        echo "https://github.com/yoheimuta/protolint/releases/download/v${PROTOLINT_VERSION}/protolint_${PROTOLINT_VERSION}_${protolint_os}_${protolint_arch}.tar.gz"
    else
        echo "Unknown tool: $tool" >&2
        return 1
    fi
}

# Function to download and install a tool
install_tool() {
    local tool=$1
    local url
    local venv_dir=$(echo $(poetry run which python) | sed 's|\(.*\)/python|\1|')
    url=$(get_download_url "$tool") || return 1

    echo "Installing $tool"
    local temp_dir
    temp_dir=$(mktemp -d)
    cd "$temp_dir"

    if ! wget -q "$url"; then
        echo "Failed to download $tool" >&2
        cd - > /dev/null
        rm -rf "$temp_dir"
        return 1
    fi

    local filename
    filename=$(basename "$url")

    case "$filename" in
        *.zip)
            unzip -q "$filename"
            ;;
        *.tar.gz)
            tar -xzf "$filename"
            ;;
        *)
            echo "Unsupported file format: $filename" >&2
            cd - > /dev/null
            rm -rf "$temp_dir"
            return 1
            ;;
    esac

    if [ "$tool" = "protoc" ]; then
        if ! which protoc &> /dev/null; then
            mv bin/protoc $venv_dir/protoc
        else
            echo "protoc is already installed, skipping..."
        fi
    elif [ "$tool" = "protolint" ]; then
        if ! which protolint &> /dev/null; then
            mv protolint $venv_dir/protolint
        else
            echo "protolint is already installed, skipping..."
        fi
    fi

    cd - > /dev/null
    rm -rf "$temp_dir"
    echo "$tool installed successfully"
}


function verify() {
    if [ $? -ne 0 ]; then
        echo "Failed to install $1" >&2
        echo 'Please make sure you have the required dependencies installed.' >&2
        exit 1
    fi
}

function install_poetry_deps() {
    local os
    local pip_executable
    local poetry_executable
    local host_poetry_executable
    host_poetry_executable=$(echo -n $(poetry env info | grep Executable |head -n 1 | awk -F: '{ print $2 }') | xargs)
    echo "Host poetry executable: $host_poetry_executable"
    echo "Setting up new poetry environment..."

    poetry env use $(which python)
    poetry_executable=$(echo -n $(poetry env info | grep Executable |head -n 1 | awk -F: '{ print $2 }') | xargs)
    echo "New poetry executable:   $poetry_executable"

    echo "Installing package dependencies via poetry..."
    echo "Using poetry executable: $poetry_executable"
    export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
    poetry install --all-extras > /dev/null || exit 1
    echo "Checking if aea is installed"
    poetry run aea --version
    echo "Done installing dependencies"

}
# Main execution

 
function set_env_file () {
    if [ ! -f ".env" ]; then
        echo "Setting up .env file"
        cp .env.template .env
    fi
}

function setup_autonomy() {
    echo "Setting up autonomy"
    echo 'Initializing the author and remote for aea and syncing packages...'

    # Extract author from config file with fallback to ci
    author=$(grep "^author:" ~/.aea/cli_config.yaml 2>/dev/null | sed 's/author:[[:space:]]*//') || author="ci"

    poetry run aea init --remote --author $author > /dev/null || exit 1
    echo 'Done initializing the author and remote for aea using the author: ' $author
    echo 'To change the author, run the command;
    `poetry run aea init --remote --author <author>`'

    if [ -f "packages/packages.json" ]; then
        echo 'Syncing packages...'
        poetry run autonomy packages sync > /dev/null || echo 'Warning: failed to sync packages as part of autonomy setup'
    fi
}

main() {
    install_poetry_deps

    install_tool "protoc" || exit 1
    install_tool "protolint" || exit 1

    verify "poetry"
    verify "protoc"
    verify "protolint"
    verify "docker"


    echo "Installation completed successfully!"
    setup_autonomy
    set_env_file
    echo '🎉You are ready to BUILD!🚀'
}

main
