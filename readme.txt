EEEPC701/4G unofficial BIOS

How to flash
-------------
- Prepare bootable flash drive with freedos.
- Copy /flash/ directory to flash stick 
- There is BIOS.ROM file in it - this is placeholder, override it with real bios rom from /bios/ folder
- Run flash.bat (it invokes special afudos.exe utility to flash unverified bios)
               

BIOS 1006.4  2025-01-25
------------

1. (bootblock) Force use CL3 profile for DRAM without SPD CL3 DDR2-400 profile.
   i.e. DDR2-800 memory sticks has only CL 4,5,6 SPD profiles, without this patch bios will use CL4 latency instead of CL3.
   This will boost you memory read/write speed and latency. See also: optimized memory timings.

2. (EC firmware) More aggresive CPU Fan RMP curve (which is managed by EC hardware timer):
   
   Factory fan mode:             Improved thresholds:
   TEMP °C <55 55 68 80 90       <40 40 45 54 59 64 70 80
     RPM % OFF 40 65 80 100      OFF 40 50 60 70 80 90 100
   
   Stock settings: The fan is off until the processor temperature rises to 55°C. 
   Then fan turns on and spins up to 40% (RPM 1450%), and only when cpu temp reaches 68°C (already overheating!) 
   it increases the rpm to 65%. When temperature reaches 80°C, the speed raises to 80%.

   Improved settings: target ~50°C 1800-2000 RPM (60%) at idle FSB 100MHz

2.1. (EC firmware) Disabled crc checking (~20-30ms startup boost)  

   Checked range 0xEC00 to 0xEE8D (654 bytes) 8-bit CRC/checksum using a 256-byte lookup table.
    
3. Fixed lcd brightness 

      MIN                                                   MAX
orig> 40 47 55 75 85 95 105 115 125 130 135 140 145 150 155 160    (900_1006_ROM)
 new> 30 40 50 60 70 80  90 100 120 140 150 170 190 210 230 246    

 There are 16 levels (0..255). Stock settings is too dim. Hotkeys: FN+F3/F4 


BIOS 1006.1:
------------

+ AHCI option (for SATA drives)

+ Fixed LCD display 'wavey lines' jitter (bug in truesata)

+ Increased default brightness

+ Added menus that was compiled, but not assigned in bios.  

	 + Configure advanced CPU settings    // Most options disabled for Celeron M
	 + NorthBridge Chipset Configuration  // DRAM timings do nothing
	 + Video Function Configuration		  // DVMT configuration, LFP type select
     + South Bridge Chipset Configuration
     + General ACPI Configuration         // ACPI2 enable 
     + USB Configuration                  // USB2 options, device emulation

     LVDS Flat Panel Types: 
		panel 1 - SSC-  96M N, pwm 200  
		panel 2 - SSC+ 100M Y, pwm 22K  <-- default
		panel 3 - SSC- 100M N, pwm 22K  
		panel 4 - SSC-  96M N, pwm 22K
		panel 5 - SSC+  96M N, pwm 22K
		panel 6 - SSC+  96M N, pwm 200

>>
>> https://youtu.be/CXM0QcKwN7g
>>

>> 
>> Based on 'truesata.rom' bios (1006 EEEPC900 adaptation)
>> http://web.archive.org/web/20191125075856/http://www.eee-pc.ru/forum/read/78/532508 
>>

+ SATA drives detected in BIOS
+ SATA drives bootable
+ 100 MHz FSB (patch in LAN boot rom)






