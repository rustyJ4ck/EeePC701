701/900 EEEPC IDE CONTROL 
-------------------------

Switch SATA controller from IDE Mode to AHCI without any BIOS updates.

Run in DOS mode: (boot from usb stick with freedos)

IDE_IDE.COM  > Set A2 = 51h /IDE Mode

IDE_AHCI.COM > Set A2 = 66h /AHCI Mode

IDE_CMOS.EXE > Show CMOS registers A2, A3 current value



; CMOS register A2:

; 2512h Reg: A2h Mask: Ch      (1100) Bits: 2 Pos: 2     <--  Configure SATA as IDE | SATA | RAID
; 2514h Reg: A2h Mask: 30h   (110000) Bits: 2 Pos: 4  	 <--  Legacy IDE Channels
; 2516h Reg: A2h Mask: C0h (11000000) Bits: 2 Pos: 6
;
; 2510h Reg: A2h Mask: 3h        (11) Bits: 2 Pos: 0  =1 <-- hyperpath
; 2518h Reg: A3h Mask: 3h        (11) Bits: 2 Pos: 0  =1 <-- used for sata conf
