EEEPC701/4G

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
>> Based on 'truesata.rom' bios (1006 EEEPC900 adaptation)
>> http://web.archive.org/web/20191125075856/http://www.eee-pc.ru/forum/read/78/532508 
>>

+ SATA drives detected in BIOS
+ SATA drives bootable
+ 100 MHz FSB (patch in LAN boot rom)






