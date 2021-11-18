#!/bin/sh
# Usage: fs2json.sh root output
./fs2json.py $1 | zstd -T0 --long -19 -o $2
