#!/bin/bash

#
# EEEPC 701/900 CPU/PCIe linux overclock utility
#
# https://github.com/rustyJ4ck/EeePC701
#

# Usage ./oc-run.sh <MHz>
# Example: ./oc-run 120    -> overclocks CPU from 100 (current) to 120 MHz

N=$1

# Check if N is provided
if [ -z "$N" ]; then
    echo "Usage: $0 <FSB_MHz>"
    echo "Example: $0 110"
    exit 1
fi

# Verify N is a valid integer/number
if ! [[ "$N" =~ ^[0-9]+$ ]]; then
    echo "ERROR: '$N' is not a valid number."
    exit 1
fi

# Verify Range (70..133) using bc for float support
IN_RANGE=$(echo "$N >= 70 && $N <= 133" | bc)

if [ "$IN_RANGE" -eq 1 ]; then
    echo "--- FSB $N MHz validated. Starting Overclock ---"
    
    # Execute the OC script with requested parameters
    sudo ./eee701_oc.sh \
        --target="$N" \
        --no-lock-check \
        --step=1 \
        --with-log 
#       --dry-run

#	./oc_stat.sh

else
    echo "ERROR: Target frequency $N MHz is out of safe range (100..133)."
    exit 1
fi
