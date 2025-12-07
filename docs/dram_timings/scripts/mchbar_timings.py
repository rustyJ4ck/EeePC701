#!/usr/bin/env python3

#
# 915gm/910gml memory timings parser
# https:#github.com/rustyJ4ck/EeePC701
#
# 1) Enable mchbar -> CALL D:\bin\mchbar-enable.bat
# 2) RW allows only one instance, so close it before running this script 
# Usage: py mchbar_timings.py --with-read  # read timings from actual hardware registers using RW.exe
# Usage: py mchbar_timings.py --simple 0x110=0x88BC10D8 0x114=0x03508111 ... # or 114=03408110 to decode timings
#

# DDR2-400 CL3-3-3-9 defaults:
#  C0DRT0  Address: 0x110 	Value: 0x987820C8 
#  C0DRT1  Address: 0x114 	Value: 0x0290D211 
#  C0DRT2  Address: 0x118 	Value: 0x80000230 
#  C0DRC0  Address: 0x120 	Value: 0x40000A06 
 
import subprocess
import sys
import re

def format_bool(v):
    return 'Y' if v else 'N'

class RegisterParser:
    def __init__(self, options):
        self.mchbar = 0xFED14000
        self.rwCmd = r'D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command='
        
        self._readTimings = '--with-read' in options
        self._simplePrint = '--simple' in options
        
        self.registers = []
        self.spd = {}
        self._regValues = {}
        
        self.getRegValuesFromOpts(options)
    
    def addRegister(self, name, address, value, bitFields):
        register_value = value
        if self._readTimings:
            register_value = self.readAddr(address)
        
        self.registers.append({
            'name': name,
            'address': address,
            'value': register_value,
            'bitFields': bitFields
        })
    
    def parseAndPrint(self):
        for register in self.registers:
            reg_id = register['address']
            if reg_id in self._regValues:
                register['value'] = self._regValues[reg_id]
            self.printRegister(register)
            print()
    
    def getRegValuesFromOpts(self, options):
        for opt in options:
            match = re.match(r'(?P<reg>[\d]{3})=(?:0x)?(?P<value>[\dA-Z]+)', opt, re.IGNORECASE)
            if match:
                reg_id = '0x' + match.group('reg')
                self._regValues[reg_id] = '0x' + match.group('value')
    
    def printRegister(self, reg):
        value = int(reg['value'], 16)
        
        print("=== {} ===".format(reg['name']), end=' ')
        print("Address: {}".format(reg['address']), end=' ')
        print("Value: {}".format(reg['value']), end=' ')
        binary_str = bin(value)[2:].zfill(32)
        spaced_binary = ' '.join(binary_str[i:i+4] for i in range(0, 32, 4))
        print(spaced_binary)
        
        print()
        
        for field in reg['bitFields']:
            fieldValue = self.extractBitField(value, field['bits'])
            
            field_id = field.get('id', '')
            field_format = field.get('format')
            description = field['description']
            field_range = field.get('range', '')
            
            formatted_value = fieldValue
            if field_format:
                if callable(field_format):
                    formatted_value = field_format(fieldValue)
                else:
                    formatted_value = field_format
            
            if self._simplePrint:
                id_display = "{} ".format(field_id) if field_id else ""
                print("  {:5} {:<4} {}".format(
                    id_display,
                    formatted_value,
                    description
                ))
            else:
                id_display = "{} ".format(field_id) if field_id else ""
                range_str = "{}..{}".format(field_range[0], field_range[1]) if field_range else ""
                
                if field_format:
                    value_display = "{})  {}".format(fieldValue, formatted_value)
                else:
                    value_display = formatted_value
                
                print("  Bits {:<7} {:<5} {:<47} {:>10} | 0x{:02X} | {:<6b} {}".format(
                    field['bits'],
                    id_display,
                    description,
                    value_display,
                    fieldValue,
                    fieldValue,
                    range_str
                ))
            
            if field_id:
                self.spd[field_id] = formatted_value
    
    def extractBitField(self, value, bitsSpec):
        v = value
        vb32 = bin(v)[2:].zfill(32)
        
        if ':' in bitsSpec:
            parts = bitsSpec.split(':')
            end = int(parts[0])
            beg = int(parts[1])
        else:
            end = int(bitsSpec)
            beg = int(bitsSpec)
        
        start_pos = 32 - end - 1
        length = 1 + end - beg
        vb = vb32[start_pos:start_pos + length]
        return int(vb, 2)
    
    def readAddr(self, address):
        cmd = self.rwCmd + '"r32 0x{:X}"'.format(self.mchbar + int(address, 16))
        print(cmd)
        try:
            result = subprocess.check_output(cmd, shell=True, universal_newlines=True)
            rwResult = result.split('=')
            return rwResult[1].strip() if len(rwResult) > 1 else False
        except subprocess.CalledProcessError:
            return False

def main():
    parser = RegisterParser(sys.argv)
    
    parser.addRegister("C0DRT0", "0x110", "0x987820C8", [
        {'bits': '31:28', 'id': 'WTP',  'description': 'Write To Precharge Command Spacing (Same bank)',     'range': [5,13], 'min': 'CL - 1 + BL/2 + WR'},
        {'bits': '27:24', 'id': 'WTR2', 'description': 'Write To Read Command Spacing (Same rank)',      'range': [4,11], 'min': 'CL - 1 + BL/2 + WTR'},
        {'bits': '23:22', 'id': 'WRD',  'description': 'Write-Read Command Spacing (Different Rank)',    'format': lambda v: 6-v, 'min': 'BL/2 + TA -1'},
        {'bits': '21:20', 'id': 'RTW',  'description': 'Read-Write Command Spacing',                    'format': lambda v: 9-v, 'min': 'BL/2 + TA +1'},
        {'bits': '19:18', 'id': 'CCDw', 'description': 'Write Command Spacing',                         'format': lambda v: 6-v, 'min': 'BL/2 + TA'},
        {'bits': '16',    'id': 'CCDr', 'description': 'Read Command Spacing',                          'format': lambda v: 5 if v else 6, 'range': [5,6]},
        {'bits': '15:11', 'id': 'RD',   'description': 'Read Delay',                                   'range': [3,31]},
        {'bits': '8:4',   'id': 'WTP2', 'description': 'Write Auto precharge to Activate (Same bank)', 'range': [4,19], 'min': 'CL -1 + BL/2 + WR + RP'},
        {'bits': '3:0',   'id': 'RTP',  'description': 'Read Auto precharge to Activate (Same bank)',  'min': 'RTPC + RP'}
    ])
    
    parser.addRegister("C0DRT1", "0x114", "0x0290D211", [
        {'bits': '29:28', 'id': 'RTPC', 'description': 'Read to Pre-charge BL/2', 'format': lambda v: {0:4,1:8}[v]},
        {'bits': '23:20', 'id': 'RAS',  'description': 'Active to Precharge Delay'},
        {'bits': '17',    'id': 'RRD',  'description': 'Activate to activate delay (clk)', 'format': lambda v: {0:2,1:3}[v]},
        {'bits': '16',                  'description': 'tRPALL Pre-All to Activate Delay'},
        {'bits': '15:11', 'id': 'RFC',  'description': 'Refresh Cycle Time', 'range': [3,31]},
        {'bits': '9:8',   'id': 'CL',   'description': 'CAS Latency', 'format': lambda v: {0:5,1:4,2:3}[v]},
        {'bits': '6:4',   'id': 'RCD',  'description': 'RAS to CAS Delay', 'format': lambda v: 1+{0:1,1:2,2:3,3:4,4:5}[v]},
        {'bits': '2:0',   'id': 'RP',   'description': 'Precharge to Activate Delay', 'format': lambda v: 1+{0:1,1:2,2:3,3:4,4:5}[v]}
    ])
    
    parser.addRegister("C0DRT2", "0x118", "0x80000230", [
        {'bits': '31:30', 'description': 'CKE Deassert Duration', 'format': lambda v: {0:1,1:'N/A',2:3,3:'N/A'}[v]},
        {'bits': '9:8',   'description': 'Power Down Exit to CS# active time', 'id': 'XPDN', 'range': [1,2], 'format': lambda v: {0:'N/A',1:1,2:2,3:1}[v]},
        {'bits': '7:5',   'description': 'DRAM Page Close Idle Timer', 'format': lambda v: {0:'N/A',1:8,2:16,3:'!res',7:'Inf'}[v]},
        {'bits': '4:0',   'description': 'DRAM Power down Idle Timer', 'format': lambda v: 'Inf' if v==31 else v, 'range': [8,16]}
    ])
    
    parser.addRegister("C0DRC0", "0x120", "0x40000906", [
        {'bits': '29',    'id': 'IC',   'description': 'Initialization Complete', 'format': format_bool},
        {'bits': '27:24',               'description': 'Active SDRAM Ranks'},
        {'bits': '15',                  'description': 'CMD copy enable (Single channel only)'},
        {'bits': '10:8',  'id': 'RMS',  'description': 'Refresh Mode Select (RMS)', 'format': lambda v: {0:'N',1:'15.6',2:'7.8'}.get(v, '')},
        {'bits': '6:4',   'id': 'SMD',  'description': 'Mode Select'},
        {'bits': '2',     'id': 'BL',   'description': 'Burst Length', 'format': lambda v: 8 if v else 4},
        {'bits': '1:0',   'id': 'DT',   'description': 'DRAM Type'}
    ])
    
    print("EEEPC 701/900 DDR2 timings parser\n")
    parser.parseAndPrint()
    
    parser.spd['WTR'] = 2
    parser.spd['WR'] = 3
    parser.spd['RC'] = parser.spd['RAS'] + parser.spd['RP']
    
    print("-------------------------------------------------------------------------------------")
    print("@ 200 MHz\t{}-{}-{}-{:<2}  (CL-RCD-RP-RAS) / {:<2}-{}-{}-{}-{}-{}  (RC-RFC-RRD-WR-WTR-RTP) \n".format(
        parser.spd['CL'],
        parser.spd['RCD'],
        parser.spd['RP'],
        parser.spd['RAS'],
        parser.spd['RC'],
        parser.spd['RFC'],
        parser.spd['RRD'],
        parser.spd['WR'],
        parser.spd['WTR'],
        parser.spd['RTP']
    ))
    
    print("SPD Memory Timings")
    print("HYMP125S64CP8-S6")
    print("@ 400 MHz\t6-6-6-18  (CL-RCD-RP-RAS) / 24-51-3-6-3-3  (RC-RFC-RRD-WR-WTR-RTP)")
    print("@ 333 MHz\t5-5-5-15  (CL-RCD-RP-RAS) / 20-43-3-5-3-3  (RC-RFC-RRD-WR-WTR-RTP)")
    print("@ 266 MHz\t4-4-4-12  (CL-RCD-RP-RAS) / 16-34-2-4-2-2  (RC-RFC-RRD-WR-WTR-RTP)")
    print("HYMP125S64CP8-Y5")
    print("@ 200 MHz\t3-3-3-9   (CL-RCD-RP-RAS) / 12-26-2-3-2-2  (RC-RFC-RRD-WR-WTR-RTP)")

if __name__ == "__main__":
    main()