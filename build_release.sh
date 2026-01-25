#!/bin/bash

# Default source path
DEFAULT_SRC="/home/dev/chromium/src"

# Check if an argument is provided, otherwise use the default
if [[ -n "$1" ]]; then
    SRC="$1"
else
    SRC="${DEFAULT_SRC}"
fi

echo "Using Chromium source directory: ${SRC}"

# Check if the source directory exists
if [[ ! -d "${SRC}" ]]; then
    echo "ERROR: Source directory '${SRC}' does not exist."
    echo "Please provide a valid source folder as an argument or modify the DEFAULT_SRC variable in the script."
    exit 1
fi

echo "Changing directory to Chromium source: ${SRC}"
cd "${SRC}" || { echo "Failed to change directory to ${SRC}. Exiting."; exit 1; }

ARCHITECTURE=arm64   # arm64 / x64 / emulator 

echo "Setting up build configuration for architecture: ${ARCHITECTURE}"
if [[ "$ARCHITECTURE" == "arm64" ]]; then
   echo "Building for arm64"
   BUILD_FOLDER="Release_arm64"
elif [[ "$ARCHITECTURE" == "x64" ]]; then
   echo "Building for x64"
   BUILD_FOLDER="Release_x64"
else
   echo "Unknown architecture; EXITING"
   exit 1
fi

VERSION_FILE="VERSION"
cd ..
# Check if the version file exists in the correct location
if [[ -f ${VERSION_FILE} ]]; then
    echo "Updating version file: ${VERSION_FILE}"

    # MAJOR
    MAJOR=$(head -n 1 ${VERSION_FILE})
    version=${MAJOR#*_}
    version=$((version + 1))
    sed -i "1s/.*/MAJOR=${version}/" ${VERSION_FILE}
    echo "Updated MAJOR version to ${version}"

    # BUILD
    BUILD=$(sed -n '3p' < ${VERSION_FILE})
    build_version=${BUILD#*_}
    build_version=$((build_version + 1))
    sed -i "s/^BUILD.*$/BUILD=${build_version}/" ${VERSION_FILE}
    echo "Updated BUILD version to ${build_version}"

    cp ${VERSION_FILE} ~/chromium/src/VERSION
    
    echo "Current version details:"
    cat ${VERSION_FILE}
else
    echo "WARNING: Version file not found in ${VERSION_FILE}. Skipping version update."
fi

cd "${SRC}" 

# Build
echo "Starting build process. This is a very long process..."
autoninja -C out/${BUILD_FOLDER} chrome_public_bundle
if [[ $? -ne 0 ]]; then
    echo "Build failed. Exiting."
    exit 1
fi
echo "Build completed successfully."

# Sign
AAB_FILE="${SRC}/out/${BUILD_FOLDER}/apks/ChromePublic.aab"

if [[ -f ${AAB_FILE} ]]; then
    echo "Signing AAB file: ${AAB_FILE}"
    apksigner sign --ks $HOME/Documents/KeyStore/store.jks --min-sdk-version 24 ${AAB_FILE}
    if [[ $? -eq 0 ]]; then
        echo "Signing completed successfully."
    else
        echo "Signing failed! You can retry signing without rebuilding by running:"
        echo "  apksigner sign --ks \$HOME/Documents/KeyStore/store.jks --min-sdk-version 24 ${AAB_FILE}"
        exit 1
    fi
else
    echo "ERROR: AAB file not found at ${AAB_FILE}. Exiting."
    exit 1
fi

echo "Script execution completed successfully!"

