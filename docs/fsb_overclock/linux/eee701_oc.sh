#!/bin/bash

#
# EEEPC 701/900 CPU/PCIe linux overclock utility
#
# https://github.com/rustyJ4ck/EeePC701
#
# Example: Overclock CPU to ~1200 MHz (target FSB = 133 MHz * 9)
# Run with --dry-run does not write to hardware registers
# sudo ./eee701_oc.sh --target=133 --no-lock-check --step=1 --with-log --dry-run
#
# Usage
# sudo eee701_oc.sh --target=120 --step=2 --dry-run
# --no-lock-check to bypass pll lock status check
# --with-cpu-freq-check validation step using /proc/cpuinfo
# --with-log write all i2c traffic to oc_i2c.log
# --set-pll-voltage=0..3 CPU PLL Differential Voltage 0.7-1.0V

# sudo modprobe i2c-dev
# sudo i2cdetect  -l
# i2c-0	smbus     	SMBus I801 adapter at 0400      	SMBus adapter

# verify the PLL is actually visible at address 0x69:
# sudo i2cdump -y -r 0x80-0x9f 0 0x69 b
#     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f    
# 80: 65 c3 ff ff f7 00 00 01 0f 07 e0 18 64 1b 24 d8 
# 90: 63 00 00 05 00 ff 04 64 63 d0 6f 00 08 08 07 80
  
# The ICS9LPR426A specifically expects the SMBus Block Write protocol, which requires a Count Byte immediately after the command/offset byte. 
# Without this byte, the PLL will misinterpret your first data byte as the count, 
# leading to a protocol mismatch and a potential system lockup or bus hang. 

# set -x  # Enable tracing

# --- Root Privilege Check ---
if [[ $EUID -ne 0 ]]; then
   echo "ERROR: This script must be run as root (use sudo)."
   exit 1
fi

# --- I2C-DEV Module Check ---

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


# --- Hardware Configuration ---
BUS=0           
ADDR="0x69"     
OFFSET=0x0  			# 0x80 smbus mode
COMMIT_DELAY=1.2
LOG_FILE="oc_i2c.log"
REG_VCPU_DIFF=0x06     	# CPU Differential Voltage Control 


# --- Fixed Fallback Values ---
B13_SS="0x1b"   
B14_SS="0x24"   

# --- Default Parameters ---
STEP=1          
TARGET=100
DRY_RUN=0
LOCK_CHECK=1
WITH_LOG=0
VCPU_DIFF=

# Parse CLI
for i in "$@"; do
  case $i in
    --target=*)    TARGET="${i#*=}"; shift ;;
    --step=*)      STEP="${i#*=}"; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --no-lock-check) LOCK_CHECK=0; shift ;;
    --with-log)    WITH_LOG=1; shift ;;
    --set-pll-voltage=*) VCPU_DIFF="${i#*=}"; shift ;;
  esac
done



# cpu -> pcie map | step += 3
get_pci_index() {
    local cpu_raw=$1
    local cpu=$(echo "scale=0; ${cpu_raw}/1" | bc)  # integer
    local pci=100
    
    if [ "$cpu" -ge 109 ]; then
        pci=103
        if [ "$cpu" -ge 113 ]; then
            # (121 - 113) / 3 = 2. 
            # 103 + (2+1)*3 = 112.
            local steps=$(( (cpu - 113) / 3 + 1 ))
            pci=$(( 103 + ((steps-0) * 3) ))
        fi
    fi

    local floor=$(( cpu - 11 ))
    if [ "$pci" -lt "$floor" ]; then pci=$floor; fi

#	if [ "$cpu" -ge 113 ]; then    
#		pci=$(echo "$pci - 3" | bc)
#	fi
    echo "$pci"
}
                 

# CPU PLL function - always uses M=24 (0x18)
# get_mn_cpu() {
#    local fvco=$1
    
    # For CPU, always M=24, N = fvco (direct mapping)
#    local m=24
#    local n=$(printf "%.0f" "$fvco")
    
    # Return M and N (N is integer)
#    echo "$m $n"
#}


# CPU PLL function with fractional support
get_mn_cpu() {
    local target_freq=$1
    
    # For CPU, always M=24
    local m=24
    
    # Calculate N = target (since Fvco = N when M=24)
    local n_required=$target_freq
    
    # Extract integer and fractional parts
    local n_int=$(echo "$n_required" | cut -d. -f1)
    local n_frac=$(echo "$n_required - $n_int" | bc -l 2>/dev/null || echo "0")
    
    # Round to nearest quarter (0, 0.25, 0.5, 0.75)
    local quarter=$(echo "scale=0; ($n_frac * 4 + 0.5)/1" | bc 2>/dev/null || echo "0")
    
    # Handle overflow (if quarter=4, increment integer)
    if [[ $quarter -eq 4 ]]; then
        quarter=0
        n_int=$((n_int + 1))
    fi
    
    # Calculate final N with exact fractional part
    case $quarter in
        0) n_final=$n_int ;;
        1) n_final=$(echo "$n_int + 0.25" | bc -l 2>/dev/null || echo "$n_int") ;;
        2) n_final=$(echo "$n_int + 0.5" | bc -l 2>/dev/null || echo "$n_int") ;;
        3) n_final=$(echo "$n_int + 0.75" | bc -l 2>/dev/null || echo "$n_int") ;;
        *) n_final=$n_int ;;
    esac
    
    echo "$m $n_final"
}

# PCIe PLL function with fractional support
get_mn_pcie() {
    local target_freq=$1
    
    # Try known frequencies first
    case "$(printf "%.1f" "$target_freq" 2>/dev/null)" in
        100.0) echo "24 100.0"; return ;;
        103.0) echo "36 154.5"; return ;;
        106.0) echo "36 159.0"; return ;;
        109.0) echo "36 163.5"; return ;;
        112.0) echo "36 168.0"; return ;;
        115.0) echo "36 172.5"; return ;;
        111.2) echo "36 166.75"; return ;;
        111.3) echo "36 167.0"; return ;;
        111.5) echo "36 167.25"; return ;;
        111.7) echo "36 167.5"; return ;;
        111.8) echo "36 167.75"; return ;;
    esac
    
    # For other frequencies, try M=36 first (better for fractional)
    local m=36
    local n_required=$(echo "scale=4; $target_freq * $m / 24" | bc -l 2>/dev/null)
    
    # Extract integer and fractional parts
    local n_int=$(echo "$n_required" | cut -d. -f1)
    local n_frac=$(echo "$n_required - $n_int" | bc -l 2>/dev/null || echo "0")
    
    # Round to nearest quarter
    local quarter=$(echo "scale=0; ($n_frac * 4 + 0.5)/1" | bc 2>/dev/null || echo "0")
    if [[ $quarter -eq 4 ]]; then
        quarter=0
        n_int=$((n_int + 1))
    fi
    
    # Calculate final N
    case $quarter in
        0) n_final=$n_int ;;
        1) n_final=$(echo "$n_int + 0.25" | bc -l 2>/dev/null || echo "$n_int") ;;
        2) n_final=$(echo "$n_int + 0.5" | bc -l 2>/dev/null || echo "$n_int") ;;
        3) n_final=$(echo "$n_int + 0.75" | bc -l 2>/dev/null || echo "$n_int") ;;
        *) n_final=$n_int ;;
    esac
    
    echo "$m $n_final"
}

# Encode to register values
encode_to_hex() {
    local m=$1
    local n=$2

#    local pll_type=$1  # "cpu" or "pcie"
#    local m=$2
#    local n=$3
    
    # Extract integer and fractional parts
    local n_int
    local frac_code=0
    
    if [[ $n == *.* ]]; then
        n_int=${n%.*}
        local frac_part=${n#*.}
        
        case $frac_part in
            25) frac_code=1 ;;  # 0.25
            5)  frac_code=2 ;;  # 0.5
            75) frac_code=3 ;;  # 0.75
            *)  frac_code=0 ;;  # 0.0
        esac
    else
        n_int=$n
        frac_code=0
    fi
    
    # Build high register: bits 7:6 = frac_code, bits 5:0 = M
    local reg_high=$(( (frac_code << 6) | (m & 0x3F) ))
    local reg_low=$n_int
    
#    if [[ $pll_type == "cpu" ]]; then
#        printf "CPU: 0x0B=0x%02X, 0x0C=0x%02X\n" "$reg_high" "$reg_low"
#    else
#        printf "PCIe: 0x0F=0x%02X, 0x10=0x%02X\n" "$reg_high" "$reg_low"
#    fi

    printf "0x%02X 0x%02X" "$reg_high" "$reg_low"
}



# Helper function to encode M/N to register values
encode_to_hex_V1() {
    local m=$1
    local n=$2
    
    # Extract integer and fractional parts
    local n_int
    local n_frac_bits=0
    
    if [[ $n == *.5 ]]; then
        n_int=${n%.*}
        n_frac_bits=2  # Binary 10 for fractional 0.5
    else
        n_int=$n
        n_frac_bits=0  # Binary 00 for integer
    fi
    
    # Build high register: bits 7:6 = n_frac_bits, bits 5:0 = M
    local reg_high=$(( (n_frac_bits << 6) | (m & 0x3F) ))
    local reg_low=$(( n_int & 0xFF ))
    
    printf "0x%02X 0x%02X" "$reg_high" "$reg_low"
    #echo "$best_m $best_n"
}


get_mn() {
    local target=$1
    local best_m=0; local best_n=0; local min_diff=999
    
    # Range constraints for N (adjust based on VCO stability if needed)
    # Since N effectively targets VCO = Target * 8, N is roughly 800-1000
    local n_min=100
    local n_max=2046

    # Iterate through M (3 to 63 per ICS9LPR datasheet)
    for m in $(seq 3 63); do
        # Calculate N for the VCO-8x architecture: N = (Target * M * 8) / 24
        # We simplify (M * 8) / 24 to (M / 3)
        local n=$(echo "scale=0; ($target * $m / 3) + 0.5/1" | bc 2>/dev/null)
        
        # Hardware Constraint: N must be EVEN (bit 0 is hardwired to 0)
        n=$(( (n / 2) * 2 ))

        if [ -n "$n" ] && [ "$n" -ge "$n_min" ] && [ "$n" -le "$n_max" ]; then
            # Calculate actual frequency achieved with this M/N pair
            local actual=$(echo "scale=4; (24 * $n) / ($m * 8)" | bc)
            
            # Absolute difference calculation
            local diff=$(echo "scale=4; if ($actual > $target) $actual - $target else $target - $actual" | bc)
            
            # Optimization: Prioritize M=24 if differences are identical (standard for 701)
            if [ $(echo "$diff < $min_diff" | bc) -eq 1 ]; then
                min_diff=$diff; best_m=$m; best_n=$n
            elif [ $(echo "$diff == $min_diff" | bc) -eq 1 ] && [ "$m" -eq 24 ]; then
                best_m=$m; best_n=$n
            fi
            
            # Exit early if exact match found
            [ $(echo "$diff == 0" | bc) -eq 1 ] && break
        fi
    done

    # Re-encode for registers:
    # Reg_Part2 = N[10:3]
    # Reg_Part1 = (N[2:1] << 6) | M[5:0]
    local reg_p2=$(( (best_n >> 3) & 0xFF ))
    local n_2_1=$(( (best_n >> 1) & 0x03 ))
    local reg_p1=$(( (n_2_1 << 6) | (best_m & 0x3F) ))

    # Output: Reg_P1 Reg_P2 M N ActualFreq
    # local final_actual=$(echo "scale=2; (24 * $best_n) / ($best_m * 8)" | bc)
    # echo "$(printf "0x%02x 0x%02x" $reg_p1 $reg_p2) $best_m $best_n $final_actual"
    echo "$best_m $best_n"
}


# High-Accuracy M/N Search 
get_mn_V1() {
    local target=$1
    local best_m=0; local best_n=0; local min_diff=999
#				 0 1 2 3   4   5   6   7   8   9   10  11  12  13 14 15 16 17 18 19 20 21 22 23 24
#   local n_min=(0 0 0 200 150 120 100 85  75  66  60  54  50  46 42 40 37 35 33 31 30 28 27 26 25)
#   local n_max=(0 0 0 400 300 240 200 171 150 133 120 109 100 92 85 80 75 70 66 63 60 57 54 52 50)
    local n_min=(0 0 0 000 000 000 60 00  035  46 000 000 100 00 00 00 00 00 00 00 30 00 00 00 25)
    local n_max=(0 0 0 000 000 000 200 000 150 133 000 000 400 00 00 00 00 00 00 00 60 00 00 00 500)

    for m in $(seq 3 24); do
        local n=$(echo "scale=0; ($target * $m / 24) + 0.5/1" | bc 2>/dev/null)
        if [ -n "$n" ] && [ -n "$n_min[$m]" ] && [ -n "$n_max[$m]" ] && [ "$n" -ge "${n_min[$m]:-999}" ] && [ "$n" -le "${n_max[$m]:-0}" ]; then
            local actual=$(echo "scale=4; 24 * $n / $m" | bc)
            local diff=$(echo "scale=4; if ($actual > $target) $actual - $target else $target - $actual" | bc)
            if [ $(echo "$diff < $min_diff" | bc) -eq 1 ]; then
                min_diff=$diff; best_m=$m; best_n=$n
            fi
            [ $(echo "$diff == 0" | bc) -eq 1 ] && break
        fi
    done
    echo "$best_m $best_n"
}


read_reg() {
    local reg_addr=$(printf "0x%02x" $(( $1 + OFFSET )))
    # Read a word (2 bytes) using 'w' mode
    local val_word=$(i2cget -y $BUS $ADDR "$reg_addr" w 2>/dev/null)
    
    if [ -n "$val_word" ]; then
        # Format is typically 0x[Byte2][Byte1] (e.g., 0x3c0f)
        # Extract the high byte (the 2nd byte read) and keep the 0x prefix
        local actual_val=$(printf "0x%s" "${val_word:2:2}")
        echo "$actual_val"
    else
        echo ""
    fi
}

write_reg() {
    local reg_addr=$(printf "0x%02x" $(( $1 + OFFSET )))
    
    # We send a block of 1 byte: [Count=1] [Value]
    # Using 's' flag for SMBus block write
    # local cmd="i2cset -y $BUS $ADDR $reg_addr 1 $2 s"

    # '0x1' is the Count Byte (length) sent manually to satisfy the PLL
    local cmd="i2cset -y $BUS $ADDR $reg_addr 0x1 $2 i"
    
    if [ "$WITH_LOG" = "1" ]; then echo "[$(date +'%T')] $cmd" >> "$LOG_FILE"; fi
    if [ "$DRY_RUN" = "0" ]; then eval "$cmd"; else echo $cmd; fi
}


read_reg_V1() {
    local reg_addr=$(printf "0x%02x" $(( $1 + OFFSET )))
    local val=$(i2cget -y $BUS $ADDR "$reg_addr" b 2>/dev/null)
    # Protection: If read fails, return empty so the caller can handle it
    echo "$val"
}

write_reg_V1() {
    local reg_addr=$(printf "0x%02x" $(( $1 + OFFSET )))
    local cmd="i2cset -y $BUS $ADDR $reg_addr $2 b"
    if [ "$WITH_LOG" = "1" ]; then echo "[$(date +'%T')] $cmd" >> "$LOG_FILE"; fi
    if [ "$DRY_RUN" = "0" ]; then eval "$cmd"; fi
}

# CPU PLL Differential Voltage Control
set_cpu_diff_voltage() {
    local n=$1
    
    # Validate input
    if [[ ! "$n" =~ ^[0-3]$ ]]; then
        echo "ERROR: CPU differential voltage N must be 0 = 0.7V, 1 = 0.8V, 2 = 0.9V, 3 = 1.0V"
        return 1
    fi
    
    # Map N to voltage and bit pattern
    local voltage
    local bits
    case $n in
        0) voltage="0.7V"; bits=$((0x00)) ;;  # Bits 7:6 = 00
        1) voltage="0.8V"; bits=$((0x40)) ;;  # Bits 7:6 = 01 (0x40 = 01000000)
        2) voltage="0.9V"; bits=$((0x80)) ;;  # Bits 7:6 = 10 (0x80 = 10000000)
        3) voltage="1.0V"; bits=$((0xC0)) ;;  # Bits 7:6 = 11 (0xC0 = 11000000)
    esac

    echo "Setting CPU differential voltage to ${voltage}  N=$n "

    # Read current register value
    local current=$(read_reg $REG_VCPU_DIFF)
    # echo "  Current Vcpudiff 0x$(printf "%02X" $REG_VCPU_DIFF): 0x$(printf "%02X" $current)"

     # Check if bits 7:6 already match desired setting
    local current_bits=$(( current & 0xC0 )) # 0xC0 = 192
    if [ $current_bits -eq $bits ]; then
        echo "  CPU differential voltage already set to ${voltage}. No change needed"
        return 0
    fi
    
    # Clear bits 7:6 (CPU differential amplitude control)
    local cleared=$(( current & ~0xC0 ))
    
    # Set new bits
    local new=$(( cleared | bits ))

	if [ "$DRY_RUN" = "0" ]; then
    	# Write to register
	    write_reg $REG_VCPU_DIFF $new
	fi
    
    echo "  CPU differential voltage set to $voltage  0x$(printf "%02X" $current_bits) -> 0x$(printf "%02X" $new)"
    
}


apply_step() {
    local cpu_f=$1; local pci_f=$2
#    read cpu_m cpu_n <<< $(get_mn "$cpu_f")
#    read pci_m pci_n <<< $(get_mn "$pci_f")

#    local v0B=$(( ((cpu_n >> 2) & 0xC0) | (cpu_m & 0x3F) ))
#    local v0C=$(( cpu_n & 0xFF ))
#    local v0F=$(( ((pci_n >> 2) & 0xC0) | (pci_m & 0x3F) ))
#    local v10=$(( pci_n & 0xFF ))

    read cpu_m cpu_n <<< $(get_mn_cpu "$cpu_f")
    read v0B v0C <<< $(encode_to_hex "$cpu_m" "$cpu_n")

    read pci_m pci_n <<< $(get_mn_pcie "$pci_f")
    read v0F v10 <<< $(encode_to_hex "$pci_m" "$pci_n")

                
	# without /1 scale=0 ignored by bc 
	local cpu_speed=$(echo "scale=0; $cpu_f * 9/1" | bc)
	local cpu_fint=$(echo "scale=0; $cpu_f/1" | bc)
	local pci_fint=$(echo "scale=0; $pci_f/1" | bc)
  
    # SSC Disable 
	if [ "$DRY_RUN" = "0" ]; then
	    # 1. Read Current Register 0x00
	    B00=$(read_reg 0x00)
	    
	    if [ -n "$B00" ]; then
	        # Convert hex string to integer
	        B00_INT=$(( B00 ))
	        
	        # Check if Bit 6 (SS_EN2) is set (0x40 = 64)
	        if [ $(( B00_INT & 0x40 )) -ne 0 ]; then
	            echo "NOTICE: Disabling Spread Spectrum (Bit 6) for stability."
	            
	            # Clear Bit 6
	            NEW_B00=$(( B00_INT & ~0x40 ))
	            
	            # Write back using SMBus Block Write format (i flag)
	            # We send: [Reg] [Length=1] [Value]
	            VAL_HEX=$(printf "0x%02x" $NEW_B00)

	            #REG_00_ADDR=$(printf "0x%02x" $(( 0x00 + OFFSET )))
	            #i2cset -y $BUS $ADDR $REG_00_ADDR 1 $VAL_HEX i
	            write_reg 0x00 "$VAL_HEX"

	            # Small delay to allow PLL to settle after SS change
	            sleep 0.1
	        fi
	    fi
	fi

    # Format arguments for Block Write (i): 
    # [Byte Count] [Data1] [Data2] ... [Data6]
    # We are writing 6 bytes (from 0x0B through 0x10)
    local start_addr=$(printf "0x%02x" $(( 0x0B + OFFSET )))
    local block_args="0x6 $(printf "0x%02x" $v0B) $(printf "0x%02x" $v0C) $B13_SS $B14_SS $(printf "0x%02x" $v0F) $(printf "0x%02x" $v10)"
    # Using 'i' flag for SMBus Block Write
    local block_cmd="i2cset -y $BUS $ADDR $start_addr $block_args i"


    # smbus mode
    # local block_args="$(printf "0x%02x" $v0B) $(printf "0x%02x" $v0C) $B13_SS $B14_SS $(printf "0x%02x" $v0F) $(printf "0x%02x" $v10)"
    # local start_addr=$(printf "0x%02x" $(( 0x0B + OFFSET )))
    # local block_cmd="i2cset -y $BUS $ADDR $start_addr $block_args s"

    if [ "$DRY_RUN" = "1" ]; then
        # echo "[DRY-RUN] CPU: ${cpu_f}MHz | PCIe: ${pci_f}MHz"
        local cpu_act=$(echo "scale=1; 24 * $cpu_n / $cpu_m" | bc)
        local pci_act=$(echo "scale=1; 24 * $pci_n / $pci_m" | bc)
        echo "          $block_cmd"
        echo "[DRY-RUN] CPU $cpu_speed MHz | FSB ${cpu_fint}MHz (M:$cpu_m N:$cpu_n -> $cpu_act) | PCIe ${pci_fint}MHz (M:$pci_m N:$pci_n -> $pci_act)"
    else
        # 1. Reset Lock Bit
        if [ "$LOCK_CHECK" = "1" ]; then
            local b00=$(read_reg 0x00)
            [ -z "$b00" ] && { echo "Error: SMBus Read Failed"; exit 1; }
            write_reg 0x00 $(( b00 & ~0x20 ))
        fi

        # 2. Block Write
        eval "$block_cmd"

        # 3. Conditional Enable MN (only once)
        local b01=$(read_reg 0x01)
        if [ -n "$b01" ] && [ $(( b01 & 0x11 )) -ne 17 ]; then
            write_reg 0x01 $(( b01 | 0x11 ))
        fi
       
	    # If we are in the high-stress zone (>120MHz), pause longer
	    # if [ "$(echo "$CURR >= 120" | bc)" -eq 1 ]; then
	    #    echo "High-Frequency Zone: Allowing VRM to settle..."
	    #    sleep 0.5
	    # else
	    #    sleep 0.1
	    # fi

        sleep "$COMMIT_DELAY"

        # 4. Lock Verification
        if [ "$LOCK_CHECK" = "1" ]; then
            local b00_check=$(read_reg 0x00)
            if [ -z "$b00_check" ] || [ $(( b00_check & 0x20 )) -eq 0 ]; then
                echo "CRITICAL: PLL Lock Failed!"; exit 1
            fi
        fi
        # echo "Applied: CPU $cpu_f MHz | PCIe $pci_f MHz"
        echo "Applied: CPU $cpu_speed MHz | FSB $cpu_fint MHz (M:$cpu_m N:$cpu_n) | PCIe $pci_fint MHz (M:$pci_m N:$pci_n)"
    fi
}

# --- Initialization 
echo "=== Eee PC 701/900 Overclocking Tool ==="

if [ -n "$VCPU_DIFF" ]; then
	set_cpu_diff_voltage $VCPU_DIFF
fi

# --- Target Range Validation (70-133 MHz)

# 1. Verify input is a valid number (integer or decimal)
if ! [[ "$TARGET" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "ERROR: Target frequency '$TARGET' is not a valid number."
    exit 1
fi

# 2. Extract the integer portion for easy range checking
TARGET_INT=$(echo "$TARGET" | cut -d'.' -f1)

# 3. Perform Range Check
if [ "$TARGET_INT" -lt 70 ] || [ "$TARGET_INT" -gt 133 ]; then
    echo "ERROR: Target frequency $TARGET MHz is out of range (70..133)."
    exit 1
fi


B11=$(read_reg 0x0B); B12=$(read_reg 0x0C)
if [ -z "$B11" ] || [ -z "$B12" ]; then
    echo "ERROR: Could not communicate with Clock Generator at $ADDR."
    echo "Check if i2c-i801 and i2c-dev modules are loaded."
    exit 1
fi

M_S=$(( B11 & 0x3F )); N_S=$(( ((B11 & 0xC0) << 2) | B12 ))
if [ "$M_S" -lt 3 ]; then CURR="100.00"; else CURR=$(echo "scale=2; 24 * $N_S / $M_S" | bc); fi


# ---- >

echo "Starting Frequency: $CURR MHz | Target: $TARGET MHz"

# Determine direction: 1 for up, -1 for down, 0 for no change
DIRECTION=$(echo "if ($TARGET > $CURR) 1 else if ($TARGET < $CURR) -1 else 0" | bc)

if [ "$DIRECTION" -eq 0 ]; then
    echo "Current frequency matches target. No action needed."
    exit 0
fi

# Main Loop
while [ "$(echo "$CURR != $TARGET" | bc)" -eq 1 ]; do
    
    # 1. Increment/Decrement CURR
    if [ "$DIRECTION" -eq 1 ]; then
        CURR=$(echo "$CURR + $STEP" | bc)
        # Prevent overshooting upward
        [ "$(echo "$CURR > $TARGET" | bc)" -eq 1 ] && CURR=$TARGET
    else
        CURR=$(echo "$CURR - $STEP" | bc)
        # Prevent overshooting downward
        [ "$(echo "$CURR < $TARGET" | bc)" -eq 1 ] && CURR=$TARGET
    fi

    # 2. Dynamic PCIe Compensation Logic
    if [ "$(echo "$CURR > 121" | bc)" -eq 1 ]; then 
       PCI=$(echo "$CURR - 10" | bc) 
    elif [ "$(echo "$CURR > 112" | bc)" -eq 1 ]; then 
        PCI=$(echo "$CURR - 10" | bc)
    elif [ "$(echo "$CURR >= 108" | bc)" -eq 1 ]; then 
        PCI=103
    else 
        PCI=100
    fi

#    read PCI <<< $(get_pci_index "$CURR")

    # 3. Apply the Step
    apply_step "$CURR" "$PCI"
    
    # Optional: Short pause to let PLL stabilize during steps
    # sleep 0.1
done

exit 0

