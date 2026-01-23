#!/bin/bash

#
# EEEPC 701/900 CPU/PCIe overclock status
#
# https://github.com/rustyJ4ck/EeePC701
#

# Show current overclock settings
# ./oc-stat.sh
# CPU 900.00 MHz | FSB 100.00 MHz (M:24 N:100) | PCIe 100.00 MHz (M:24 N:100)

# sudo i2cdump -y -r 0x80-0x9f 0 0x69 b          ; PLL data: offset 0x80 +20bytes

#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f    0123456789abcdef
# 00: 65 d3 ff ff f7 00 00 01 0f 07 e0 0f 3f 1b 24 0c    e?..?..???????$?
# 10: 32 00 00 05 00 ff 04 64 63 d0 6f 00 08 08 07 80    2..?..?dc?o.????

#!/bin/bash

BUS=0
ADDR="0x69"

# I2C-DEV Module Check 

# Check if /dev/i2c-0 exists (standard indicator for i2c-dev)
if [ ! -e /dev/i2c-0 ]; then
    echo "NOTICE: i2c-dev interface not found. Attempting to load module..."
    
    # Try to load the module (requires root)
    if sudo modprobe i2c-dev; then
        # Give the kernel a moment to create the device nodes
        sleep 0.5
        echo "SUCCESS: i2c-dev loaded."
    else
        echo "ERROR: Failed to load i2c-dev."
        exit 1
    fi
fi

# Final verification: Check if i2c-dev is actually in the kernel module list
if ! lsmod | grep -q "^i2c_dev"; then
    echo "ERROR: i2c-dev is not loaded."
    exit 1
fi


# Capture dump (0x80 to 0x9f)
DUMP=$(sudo i2cdump -y -r 0x80-0x9f $BUS $ADDR b 2>/dev/null)

if [ -z "$DUMP" ]; then
    echo "ERROR: SMBus communication failed."
    exit 1
fi

# Fixed extraction function
get_val() {
    local row=$1  # e.g., "80" or "90"
    local col=$2  # 0-15
    # Row starts at header, so col 0 is field 2, col 1 is field 3, etc.
    echo "$DUMP" | grep "^$row:" | awk -v c=$((col + 2)) '{print "0x"$c}'
}

# CPU: Reg 0x0B (offset 0x8B) and 0x0C (offset 0x8C)
RAW_0B=$(get_val "80" 11)
RAW_0C=$(get_val "80" 12)

M_CPU=$(( RAW_0B & 0x3F ))
N_CPU=$(( ((RAW_0B & 0xC0) << 2) | RAW_0C ))

# PCIe: Reg 0x0F (offset 0x8F) and 0x10 (offset 0x90)
RAW_0F=$(get_val "80" 15)
RAW_10=$(get_val "90" 0) # Register 0x10 is row 90, column 0

# A4 A6
M_PCI=$(( RAW_0F & 0x3F ))
#N_PCI=$(( ((RAW_0F & 0xC0) << 2) | RAW_10 ))
N_PCI=$(( $RAW_10 ))

# Calculate Frequencies
calc_freq() {
    if [ "$1" -eq 0 ]; then echo "0.00"; else
        echo "scale=2; 24 * $2 / $1" | bc
    fi
}


F_CPU=$(calc_freq $M_CPU $N_CPU)
F_PCI=$(calc_freq $M_PCI $N_PCI)
CPU_SPEED=$(echo "$F_CPU * 9" | bc);

echo "CPU $CPU_SPEED MHz | FSB $F_CPU MHz (M:$M_CPU N:$N_CPU) | PCIe $F_PCI MHz (M:$M_PCI N:$N_PCI)"
