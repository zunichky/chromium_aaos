#!/bin/bash
cd src
git fetch
git reset --hard
git pull
gclient sync
cp ~/chromium/apply_patches.sh .
./apply_patches.sh
rm apply_patches.sh
# Shouldn't have to run "gn args out/Release" 
gclient runhooks
