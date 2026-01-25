"""
EEEPC 701/900 EC Monitor

# Run:  
py ec_monitor_gauge.py  --com=15 --skip-raw

- Connects to serial port and monitors EC data in real-time
- Parses CPU temperature from hex to decimal (e.g., 0x3D → 61°C)
- Extracts fan PWM values (e.g., 0x46 → 70)
- Handles multiple temperature patterns (direct, REC=, oXX,o)
- Displays clean output with timestamps
- Test mode with your provided sample data

# Required:

pip install pyserial

# Usage:

# Windows - Using COM port number
python ec_monitor.py --com=3
python ec_monitor.py -c 4
python ec_monitor.py --com=5 --baudrate=9600

# Windows/Linux - Using full port path
python ec_monitor.py --port=COM3
python ec_monitor.py -p /dev/ttyUSB0

# Linux
python ec_monitor.py --com=0  # Will try to connect to COM0 (not typical for Linux)
python ec_monitor.py --port=/dev/ttyACM0

# List available ports
python ec_monitor.py --list-ports

# Test with sample data
python ec_monitor.py --test

# With hex values
python ec_monitor.py --com=3 --with-hex

# Custom gauge configuration
python ec_monitor.py --com=3 --gauge-min=30 --gauge-max=80 --gauge-width=60

# Custom bar thresholds
python ec_monitor.py --com=3 --gauge-bar-thresholds=50,70,80

# Combined options
python ec_monitor.py --com=3 --skip-raw --with-hex --gauge-width=60 --gauge-bar-thresholds=55,75,90

# Debug
python ec_monitor.py --com=3 --debug --with-hex


"""

import serial
import time
import re
import sys
from datetime import datetime

class EC_Parser:
    def __init__(self, port, baudrate=115200, skip_raw=False, with_hex=False, debug=False):
        """
        Initialize the EC Parser with serial connection parameters
        
        Args:
            port: Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Baud rate (default: 115200)
            skip_raw: Skip displaying raw EC chatter (default: False)
            with_hex: Display hex values for temperature and fan (default: False)
            debug: Show debug information including all raw data (default: False)
        """
        self.port = port
        self.baudrate = baudrate
        self.skip_raw = skip_raw
        self.with_hex = with_hex
        self.debug = debug
        self.ser = None
        self.current_temp = None
        self.fan_mode = None
        self.fan_pwm = None
        self.fan_pwm_percent = None  # Store the last PWM percentage
        self.prev_temp = None  # Store previous temperature for gauge comparison
        self.prev_fan_pwm = None  # Store previous fan PWM for change detection
        
        # State tracking for multi-line patterns
        self.expecting_temp = False
        self.expecting_fan = False
        
        # Debug statistics
        self.stats = {
            'total_lines': 0,
            'temp_lines': 0,
            'fan_lines': 0,
            'other_lines': 0
        }
        
    def create_temperature_gauge(self, temperature, min_temp=40, max_temp=75, width=50, thresholds=None):
        """
        Create an ASCII temperature gauge bar scaled from min_temp to max_temp
        
        Args:
            temperature: Temperature in Celsius
            min_temp: Minimum temperature for gauge (default: 40)
            max_temp: Maximum temperature for gauge (default: 75)
            width: Width of the gauge in characters
            thresholds: List of threshold temperatures for bar characters (default: [60, 75, 85])
            
        Returns:
            str: Formatted gauge string
        """
        # Default thresholds if not provided
        if thresholds is None:
            thresholds = [60, 75, 85]
            
        # Ensure we have exactly 3 thresholds
        if len(thresholds) < 3:
            thresholds = thresholds + [85] * (3 - len(thresholds))
        elif len(thresholds) > 3:
            thresholds = thresholds[:3]
        
        # Ensure temperature is within bounds for display
        temp_display = temperature
        
        # Calculate how many filled characters we need
        # Scale temperature to gauge width (accounting for borders and labels)
        temp_range = max_temp - min_temp
        if temp_range <= 0:
            temp_range = 1  # Avoid division by zero
            
        # Calculate position (0 to width-6 for filled chars)
        gauge_width_for_fill = width - 6  # Account for labels and borders
        
        # Map temperature to gauge position
        if temperature < min_temp:
            filled_chars = 0
        elif temperature > max_temp:
            filled_chars = gauge_width_for_fill
        else:
            filled_chars = int(((temperature - min_temp) / temp_range) * gauge_width_for_fill)
        
        # Ensure filled_chars is within bounds
        filled_chars = max(0, min(gauge_width_for_fill, filled_chars))
        empty_chars = gauge_width_for_fill - filled_chars
        
        # Use different characters based on temperature thresholds
        if temperature < thresholds[0]:  # Default: <60°C
            fill_char = '░'  # Light fill for cool
        elif temperature < thresholds[1]:  # Default: <75°C
            fill_char = '▒'  # Medium fill for warm
        elif temperature < thresholds[2]:  # Default: <85°C
            fill_char = '▓'  # Heavy fill for hot
        else:
            fill_char = '█'  # Solid for very hot
            
        # Build the gauge
        gauge = f"{min_temp} |{fill_char * filled_chars}{' ' * empty_chars}|{max_temp}°C"
        
        # Add temperature indicator with trend arrow
        indicator_pos = max(len(str(min_temp)) + 2, 
                           min(width - len(str(max_temp)) - 3, 
                               len(str(min_temp)) + 2 + filled_chars))
        
        # Create trend indicator
        trend = ""
        if self.prev_temp is not None:
            if temperature > self.prev_temp:
                trend = " ↗"
            elif temperature < self.prev_temp:
                trend = " ↘"
            else:
                trend = " →"
        
        # Build the gauge with indicator
        gauge_with_indicator = list(gauge)
        if len(str(min_temp)) + 2 <= indicator_pos < len(gauge_with_indicator):
            gauge_with_indicator[indicator_pos] = '│'  # Temperature indicator
            
        gauge_str = ''.join(gauge_with_indicator)
        
        # Store current temp as previous for next comparison
        self.prev_temp = temperature
        
        return gauge_str + trend
        
    def connect(self):
        """Establish serial connection"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False
            
    def disconnect(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial connection closed")
            
    def parse_line(self, line):
        """
        Parse a single line of data from the EC
        
        Args:
            line: Raw line from serial
            
        Returns:
            dict: Parsed data containing temperature and/or fan info
        """
        parsed_data = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'temperature_c': None,
            'temperature_hex': None,
            'fan_mode': None,
            'fan_pwm': None,
            'fan_pwm_hex': None,
            'fan_pwm_percent': None,
            'raw_line': line.strip()
        }
        
        # Remove line endings
        clean_line = line.strip().replace('\r', '').replace('\n', '')
        
        if not clean_line:
            return parsed_data
        
        # Check if we're expecting temperature from previous line (after CPUTmp)
        if self.expecting_temp:
            # The temperature line can be a simple hex OR a full temperature line
            # Like: "3C" or "37,T(A0,S0)wTTTCPUTmp"
            
            # Try to extract temperature from the beginning of the line
            temp_match = re.search(r'^([0-9A-F]{2})', clean_line)
            if temp_match:
                temp_hex = temp_match.group(1)
                try:
                    temp_c = int(temp_hex, 16)
                    # Filter temperatures to valid range 40-80°C
                    if 40 <= temp_c <= 80:  # Valid CPU temp range
                        parsed_data['temperature_c'] = temp_c
                        parsed_data['temperature_hex'] = temp_hex
                        self.current_temp = temp_c
                        self.stats['temp_lines'] += 1
                        if self.debug:
                            print(f"[{parsed_data['timestamp']}] DEBUG: Got temperature {temp_c}°C (0x{temp_hex}) from line after CPUTmp")
                except ValueError:
                    pass
            else:
                if self.debug:
                    print(f"[{parsed_data['timestamp']}] DEBUG: Could not extract temperature from line after CPUTmp: {clean_line}")
            self.expecting_temp = False
        
        # Check if we're expecting fan data from previous line (after CFan idx,PWM)
        elif self.expecting_fan:
            # Fan data should be in format "04,46" (mode, pwm) - two hex values
            fan_match = re.search(r'^([0-9A-F]{2}),([0-9A-F]{2})', clean_line)
            if fan_match:
                mode_hex = fan_match.group(1)
                pwm_hex = fan_match.group(2)
                try:
                    mode = int(mode_hex, 16)
                    pwm = int(pwm_hex, 16)  # This is already the percentage
                    parsed_data['fan_mode'] = mode
                    parsed_data['fan_pwm'] = pwm
                    parsed_data['fan_pwm_hex'] = pwm_hex
                    parsed_data['fan_pwm_percent'] = pwm  # Store as percentage
                    
                    # Update class instance variables
                    self.fan_mode = mode
                    self.fan_pwm = pwm
                    self.fan_pwm_percent = pwm
                    self.stats['fan_lines'] += 1
                    
                    if self.debug:
                        print(f"[{parsed_data['timestamp']}] DEBUG: Got fan data: mode={mode} (0x{mode_hex}), pwm={pwm}% (0x{pwm_hex})")
                except ValueError:
                    if self.debug:
                        print(f"[{parsed_data['timestamp']}] DEBUG: Could not parse fan data from: {clean_line}")
            else:
                if self.debug:
                    print(f"[{parsed_data['timestamp']}] DEBUG: Expected fan data (XX,XX) after CFan idx,PWM but got: {clean_line}")
            self.expecting_fan = False
            # Don't return here - allow other parsing on this line
        
        # Now check for patterns in the current line (not in expecting state)
        # Check for temperature patterns first (they are more common)
        
        # Pattern 1: Line starts with hex and contains CPUTmp (e.g., "37,T(A0,S0)wTTTCPUTmp")
        temp_match1 = re.search(r'^([0-9A-F]{2}),.*CPUTmp', clean_line)
        if temp_match1:
            temp_hex = temp_match1.group(1)
            try:
                temp_c = int(temp_hex, 16)
                # Filter temperatures to valid range 40-80°C
                if 40 <= temp_c <= 80:  # Valid CPU temp range
                    parsed_data['temperature_c'] = temp_c
                    parsed_data['temperature_hex'] = temp_hex
                    self.current_temp = temp_c
                    self.stats['temp_lines'] += 1
                    if self.debug:
                        print(f"[{parsed_data['timestamp']}] DEBUG: Got temperature {temp_c}°C (0x{temp_hex}) from inline CPUTmp")
            except ValueError:
                pass
        
        # Pattern 2: Line starts with oXX,o,TTCPUTmp (e.g., "o39,o,T(A0,S0)wTTTCPUTmp")
        temp_match2 = re.search(r'^o([0-9A-F]{2}),o.*CPUTmp', clean_line)
        if temp_match2 and not parsed_data['temperature_c']:
            temp_hex = temp_match2.group(1)
            try:
                temp_c = int(temp_hex, 16)
                # Filter temperatures to valid range 40-80°C
                if 40 <= temp_c <= 80:  # Valid CPU temp range
                    parsed_data['temperature_c'] = temp_c
                    parsed_data['temperature_hex'] = temp_hex
                    self.current_temp = temp_c
                    self.stats['temp_lines'] += 1
                    if self.debug:
                        print(f"[{parsed_data['timestamp']}] DEBUG: Got temperature {temp_c}°C (0x{temp_hex}) from oXX,o pattern")
            except ValueError:
                pass
        
        # Pattern 3: Line starts with hex and comma (e.g., "37,T(A0,S0)TTwTCPUTmp")
        temp_match3 = re.search(r'^([0-9A-F]{2}),', clean_line)
        if temp_match3 and not parsed_data['temperature_c']:
            # Additional check to avoid parsing fan data as temperature
            # Check if this looks like a temperature line (has T( or wT or similar)
            if re.search(r'T\(|wT|Tw', clean_line):
                temp_hex = temp_match3.group(1)
                try:
                    temp_c = int(temp_hex, 16)
                    # Filter temperatures to valid range 40-80°C
                    if 40 <= temp_c <= 80:  # Valid CPU temp range
                        parsed_data['temperature_c'] = temp_c
                        parsed_data['temperature_hex'] = temp_hex
                        self.current_temp = temp_c
                        self.stats['temp_lines'] += 1
                        if self.debug:
                            print(f"[{parsed_data['timestamp']}] DEBUG: Got temperature {temp_c}°C (0x{temp_hex}) from hex at line start")
                except ValueError:
                    pass
        
        # Pattern 4: REC=xx (recovery mode temperature)
        rec_match = re.search(r'REC=([0-9A-F]{2})', clean_line)
        if rec_match and not parsed_data['temperature_c']:
            temp_hex = rec_match.group(1)
            try:
                temp_c = int(temp_hex, 16)
                # Filter temperatures to valid range 40-80°C
                if 40 <= temp_c <= 80:  # Valid CPU temp range
                    parsed_data['temperature_c'] = temp_c
                    parsed_data['temperature_hex'] = temp_hex
                    self.current_temp = temp_c
                    self.stats['temp_lines'] += 1
                    if self.debug:
                        print(f"[{parsed_data['timestamp']}] DEBUG: Got temperature {temp_c}°C (0x{temp_hex}) from REC pattern")
            except ValueError:
                pass
        
        # Now check for fan patterns (after temperature checks)
        # Pattern 1: Line contains CFan idx,PWM (e.g., "36,CFan idx,PWM")
        if 'CFan idx,PWM' in clean_line:
            # This line might also have a temperature at the beginning
            # Extract the fan PWM if it's in XX,XX format at the beginning
            fan_match = re.search(r'^([0-9A-F]{2}),([0-9A-F]{2}),CFan idx,PWM', clean_line)
            if fan_match:
                mode_hex = fan_match.group(1)
                pwm_hex = fan_match.group(2)
                try:
                    mode = int(mode_hex, 16)
                    pwm = int(pwm_hex, 16)  # This is already the percentage
                    parsed_data['fan_mode'] = mode
                    parsed_data['fan_pwm'] = pwm
                    parsed_data['fan_pwm_hex'] = pwm_hex
                    parsed_data['fan_pwm_percent'] = pwm  # Store as percentage
                    
                    # Update class instance variables
                    self.fan_mode = mode
                    self.fan_pwm = pwm
                    self.fan_pwm_percent = pwm
                    self.stats['fan_lines'] += 1
                    
                    if self.debug:
                        print(f"[{parsed_data['timestamp']}] DEBUG: Got fan data from CFan line: mode={mode} (0x{mode_hex}), pwm={pwm}% (0x{pwm_hex})")
                except ValueError:
                    if self.debug:
                        print(f"[{parsed_data['timestamp']}] DEBUG: Could not parse fan data from CFan line: {clean_line}")
            else:
                # Just CFan idx,PWM without data - set expecting_fan for next line
                self.expecting_fan = True
                if self.debug:
                    print(f"[{parsed_data['timestamp']}] DEBUG: Found CFan idx,PWM, expecting fan data on next line")
        
        # Check for CPUTmp pattern that indicates next line has temperature
        elif clean_line == 'CPUTmp':
            self.expecting_temp = True
            if self.debug:
                print(f"[{parsed_data['timestamp']}] DEBUG: Found CPUTmp, expecting temperature on next line")
        
        # Check if fan PWM changed and add to parsed data
        if parsed_data['fan_pwm'] is not None:
            # Check if this is a change from previous value
            if self.prev_fan_pwm is not None and parsed_data['fan_pwm'] != self.prev_fan_pwm:
                parsed_data['fan_changed'] = True
            else:
                parsed_data['fan_changed'] = False
            
            # Update previous fan PWM
            self.prev_fan_pwm = parsed_data['fan_pwm']
        
        # Update statistics for unparsed lines
        if parsed_data['temperature_c'] is None and parsed_data['fan_pwm'] is None and clean_line:
            self.stats['other_lines'] += 1
            
        return parsed_data
        
    def display_data(self, data, min_temp=40, max_temp=75, gauge_width=50, thresholds=None):
        """Display parsed data in a readable format with temperature gauge on same line"""
        if data['temperature_c'] is not None:
            # Create temperature gauge (scaled min_temp-max_temp°C)
            gauge = self.create_temperature_gauge(
                data['temperature_c'], 
                min_temp=min_temp, 
                max_temp=max_temp, 
                width=gauge_width,
                thresholds=thresholds
            )
            
            # Get fan PWM percentage (use last known value if not in current data)
            fan_percent = self.fan_pwm_percent
            
            # Format fan info with or without hex values
            if fan_percent is not None:
                if self.with_hex:
                    fan_info = f"FAN:{fan_percent:3d}% (0x{self.fan_pwm:02X}) CPU:{data['temperature_c']:3d}°C"
                else:
                    fan_info = f"FAN:{fan_percent:3d}% CPU:{data['temperature_c']:3d}°C"
            else:
                fan_info = f"FAN: N/A  CPU:{data['temperature_c']:3d}°C"
            
            # Add hex value for temperature if requested
            hex_info = f" (0x{data['temperature_hex']})" if self.with_hex else ""
            
            # Build output line
            print(f"[{data['timestamp']}] {fan_info}{hex_info} {gauge}")
            
        elif data['fan_pwm_percent'] is not None:
            # Display fan change information
            mode_info = f"Mode={data['fan_mode']}, " if data['fan_mode'] is not None else ""
            hex_info = f" (0x{data['fan_pwm_hex']}, {data['fan_pwm_percent']}%)" if self.with_hex else f" ({data['fan_pwm_percent']}%)"
            
            # Add direction indicator
            direction = ""
            if self.prev_fan_pwm is not None:
                if data['fan_pwm'] > self.prev_fan_pwm:
                    direction = " ↑"
                elif data['fan_pwm'] < self.prev_fan_pwm:
                    direction = " ↓"
            
            print(f"[{data['timestamp']}] Fan PWM changed: {mode_info}PWM={data['fan_pwm']}{hex_info}{direction}")
                
        # Show raw data for debugging only if not skipped OR if debug mode is on
        elif (not self.skip_raw or self.debug) and data['raw_line']:
            # Show raw line for debugging if it contains data
            if len(data['raw_line']) > 2:  # Don't show empty or very short lines
                prefix = "DEBUG" if self.debug else "Raw"
                print(f"[{data['timestamp']}] {prefix}: {data['raw_line']}")
                
    def monitor(self, min_temp=40, max_temp=75, gauge_width=50, thresholds=None):
        """Main monitoring loop"""
        if not self.ser or not self.ser.is_open:
            print("Serial port not open. Call connect() first.")
            return
            
        # Format threshold info for display
        if thresholds:
            threshold_info = f"Bar thresholds: ░<{thresholds[0]}°C ▒<{thresholds[1]}°C ▓<{thresholds[2]}°C █>={thresholds[2]}°C"
        else:
            threshold_info = "Bar thresholds: ░<60°C ▒<75°C ▓<85°C █>=85°C"
        
        print("\n" + "="*100)
        print("ENE KB3310 EC Monitor")
        print("="*100)
        print(f"Temperature Gauge: {min_temp}-{max_temp}°C, Width: {gauge_width} chars")
        print(threshold_info)
        print("Parsing patterns:")
        print("  - Temperature: Line containing CPUTmp or starting with hex and T( pattern")
        print("  - Fan RPM: Line containing 'CFan idx,PWM' or expecting fan data on next line")
        print("  - Multi-line: 'CPUTmp' alone → next line has temperature")
        print(f"Temperature filter: 40-80°C (will ignore values outside this range)")
        print(f"Fan PWM range: 0-100% (hex value is already percentage)")
        if self.with_hex:
            print("Hex values are enabled")
        if self.skip_raw and not self.debug:
            print("Raw EC chatter is disabled (use --show-raw to enable)")
        if self.debug:
            print("DEBUG mode enabled - showing all raw data and parsing state")
        print("Press Ctrl+C to exit")
        print("="*100 + "\n")
        
        buffer = ""
        
        try:
            while True:
                # Read available data
                if self.ser.in_waiting > 0:
                    try:
                        # Read and decode
                        raw_data = self.ser.read(self.ser.in_waiting)
                        buffer += raw_data.decode('ascii', errors='ignore')
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            
                            # Update total line count
                            self.stats['total_lines'] += 1
                            
                            # Parse the line
                            parsed = self.parse_line(line)
                            
                            # Display parsed information with gauge
                            self.display_data(parsed, min_temp, max_temp, gauge_width, thresholds)
                            
                    except UnicodeDecodeError:
                        if not self.skip_raw or self.debug:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Decode error")
                        buffer = ""
                        
                # Small delay to prevent CPU hogging
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            # Print statistics if debug mode is enabled
            if self.debug:
                self.print_statistics()
                
    def print_statistics(self):
        """Print parsing statistics"""
        print("\n" + "="*60)
        print("Parsing Statistics:")
        print("="*60)
        print(f"Total lines processed: {self.stats['total_lines']}")
        print(f"Temperature lines parsed: {self.stats['temp_lines']}")
        print(f"Fan lines parsed: {self.stats['fan_lines']}")
        print(f"Other/unparsed lines: {self.stats['other_lines']}")
        
        if self.stats['total_lines'] > 0:
            success_rate = ((self.stats['temp_lines'] + self.stats['fan_lines']) / self.stats['total_lines']) * 100
            print(f"Parsing success rate: {success_rate:.1f}%")
        print("="*60)
            
    def test_with_sample_data(self, min_temp=40, max_temp=75, gauge_width=50, thresholds=None):
        """Test the parser with the provided sample data"""
        print("Testing parser with sample data...")
        print("="*100)
        print(f"Temperature Gauge: {min_temp}-{max_temp}°C, Width: {gauge_width} chars")
        if thresholds:
            threshold_info = f"Bar thresholds: ░<{thresholds[0]}°C ▒<{thresholds[1]}°C ▓<{thresholds[2]}°C █>={thresholds[2]}°C"
        else:
            threshold_info = "Bar thresholds: ░<60°C ▒<75°C ▓<85°C █>=85°C"
        print(threshold_info)
        print("Parsing patterns:")
        print("  - Temperature: Line containing CPUTmp or starting with hex and T( pattern")
        print("  - Fan RPM: Line containing 'CFan idx,PWM' or expecting fan data on next line")
        print("  - Multi-line: 'CPUTmp' alone → next line has temperature")
        print(f"Temperature filter: 40-80°C (will ignore values outside this range)")
        print(f"Fan PWM range: 0-100% (hex value is already percentage)")
        if self.with_hex:
            print("Hex values are enabled")
        if self.debug:
            print("DEBUG mode enabled - showing all raw data and parsing state")
        print("="*100)
        
        # Test data based on the actual debug output
        test_data = """CPUTmp
37,T(A0,S0)wTTTCPUTmp
37,T(A0,S0)TTwTCPUTmp
CPUTmp
37,T(A0,S0)TTTCPUTmp
37,T(A0,S0)wTTTCPUTmp
CPUTmp
37,T(A0,S0)TTwTCPUTmp
37,T(A0,S0)TTTCPUTmp
36,CFan idx,PWM
03,3C,T(A0,S0)
e80,d51,
REC=3C,51"""
        
        lines = test_data.split('\n')
        for line in lines:
            # Simulate timestamp
            parsed_data = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'raw_line': line.strip()
            }
            
            # Update total line count
            self.stats['total_lines'] += 1
            
            if self.debug and line.strip():
                print(f"[{parsed_data['timestamp']}] DEBUG Raw: {line.strip()}")
            
            # Parse the line
            parsed = self.parse_line(line)
            
            # Display parsed information with gauge
            self.display_data(parsed, min_temp, max_temp, gauge_width, thresholds)
            
        print("\n" + "="*100)
        print("Test Summary:")
        print(f"Last CPU Temperature: {self.current_temp}°C")
        if self.with_hex and self.fan_pwm is not None:
            print(f"Last Fan Settings: Mode={self.fan_mode}, PWM={self.fan_pwm} (0x{self.fan_pwm:02X}, {self.fan_pwm_percent}%)")
        elif self.fan_pwm is not None:
            print(f"Last Fan Settings: Mode={self.fan_mode}, PWM={self.fan_pwm} ({self.fan_pwm_percent}%)")
        else:
            print("Last Fan Settings: None")
        
        # Print statistics if debug mode is enabled
        if self.debug:
            self.print_statistics()
            
        print("="*100)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ENE KB3310 EC Monitor with Temperature Gauge',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --com=3                     # Windows: Connect to COM3
  %(prog)s --com=4 --skip-raw          # Windows: COM4, skip raw chatter
  %(prog)s --port=/dev/ttyUSB0         # Linux: Connect to /dev/ttyUSB0
  %(prog)s --test                      # Test with sample data
  %(prog)s --com=3 --with-hex          # Show hex values for temp and fan
  %(prog)s --com=3 --debug             # Show debug output with all raw data
  %(prog)s --com=3 --gauge-min=30 --gauge-max=80 --gauge-width=60
  %(prog)s --com=3 --gauge-bar-thresholds=50,70,80
  %(prog)s --com=3 --skip-raw --debug --with-hex --gauge-width=60
        """
    )
    
    # Group for serial port options (mutually exclusive in practice)
    port_group = parser.add_mutually_exclusive_group()
    port_group.add_argument('--port', '-p', type=str,
                           help='Full serial port path (e.g., COM3, /dev/ttyUSB0)')
    port_group.add_argument('--com', '-c', type=int,
                           help='Windows COM port number (e.g., 3 for COM3)')
    
    parser.add_argument('--baudrate', '-b', type=int, default=115200,
                       help='Baud rate (default: 115200)')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Test with sample data instead of serial port')
    parser.add_argument('--list-ports', '-l', action='store_true',
                       help='List available serial ports')
    parser.add_argument('--width', '--gauge-width', type=int, default=50,
                       help='Width of the temperature gauge (default: 50)')
    parser.add_argument('--skip-raw', '-r', action='store_true',  # default to show raw data
                       help='Skip displaying raw EC chatter')
    parser.add_argument('--show-raw', dest='skip_raw', action='store_false',
                       help='Show raw EC chatter (default)')
    parser.add_argument('--min-temp', '--gauge-min', type=int, default=40,
                       help='Minimum temperature for gauge (default: 40°C)')
    parser.add_argument('--max-temp', '--gauge-max', type=int, default=75,
                       help='Maximum temperature for gauge (default: 75°C)')
    parser.add_argument('--gauge-bar-thresholds', type=str, default='60,75,85',
                       help='Temperature thresholds for bar characters as comma-separated values (default: 60,75,85)')
    parser.add_argument('--with-hex', action='store_true',
                       help='Display hex values for temperature and fan PWM (default: False)')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Show debug output including all raw data and parsing state (default: False)')
    
    args = parser.parse_args()
    
    # List available ports if requested
    if args.list_ports:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        if not ports:
            print("No serial ports found.")
        else:
            print("Available serial ports:")
            for port in ports:
                print(f"  {port.device}: {port.description}")
        return
    
    # Parse gauge bar thresholds
    try:
        thresholds = [int(t.strip()) for t in args.gauge_bar_thresholds.split(',')]
        if len(thresholds) != 3:
            print(f"Warning: Expected 3 thresholds, got {len(thresholds)}. Using defaults: 60,75,85")
            thresholds = [60, 75, 85]
    except ValueError:
        print(f"Error: Invalid thresholds format '{args.gauge_bar_thresholds}'. Using defaults: 60,75,85")
        thresholds = [60, 75, 85]
    
    # Determine the port to use
    if args.com is not None:
        # Use COM port number
        port = f'COM{args.com}'
    elif args.port is not None:
        # Use full port path
        port = args.port
    else:
        # No port specified
        port = None
    
    # Create parser instance with all options
    parser_instance = EC_Parser(port, args.baudrate, args.skip_raw, args.with_hex, args.debug)
    
    if args.test:
        # Run test with sample data
        parser_instance.test_with_sample_data(args.min_temp, args.max_temp, args.width, thresholds)
    else:
        # Connect to serial port
        if not port:
            print("\nError: No serial port specified!")
            print("\nPlease specify a serial port using one of these options:")
            print("  --com=N        : Windows COM port number (e.g., --com=3 for COM3)")
            print("  --port PORT    : Full serial port path (e.g., --port COM3 or --port /dev/ttyUSB0)")
            print("  --list-ports   : List available serial ports")
            sys.exit(1)
            
        if not parser_instance.connect():
            print(f"\nFailed to connect to {port}.")
            print("Make sure the port is correct and the device is connected.")
            sys.exit(1)
            
        # Start monitoring
        try:
            parser_instance.monitor(args.min_temp, args.max_temp, args.width, thresholds)
        finally:
            parser_instance.disconnect()


if __name__ == "__main__":
    main()