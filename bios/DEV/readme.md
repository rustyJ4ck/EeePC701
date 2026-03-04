#### DEV BIOS EEEPC 701/900 (Celeron M)

This firmware version is designed for TESTING purposes only. There are no guarantees whatsoever; use it at your own risk.

> [!CAUTION]
> I was informed that the firmware can break the device (the Eee 900 does not wake up after going into sleep mode).
> Be sure to disable windows XP sleep mode if you want try this firmware.

Currently testing proper BCLK 133 MHz overclocking (via bootblock) before MRC code trains the MCH/DRAM and system acknowledge 133 MHz bus. 

Some features may be broken (like sleep mode)

BIOS options:  

**DRAM Frequency** = 533 -> Enable BCLK 133 MOD

**Configure DRAM Timing by SPD**
= DISABLED -> will choose tightest possible timings to improve latency

![133 BIOS Setup](https://github.com/rustyJ4ck/EeePC701/blob/main/docs/images/bios_bclk.jpg?raw=true)

To run 133 BCLK with CL3 DRAM, CPU Vcore need to be adjusted to 0.94v [CPU Voltmod](https://github.com/rustyJ4ck/EeePC701/tree/main/docs/voltmod_cpu)* 

##### EEEPC-900
The BIOS defaults to using the 701 screen profile. To enable a 900 resolution, you need to manually choose this option in the BIOS setup: 
Advanced -> NB -> Video -> LFP Panel type:

![133 BIOS Setup](https://github.com/rustyJ4ck/EeePC701/blob/main/docs/images/900_lfp.jpg?raw=true)

Aida memory benchmark (BCLK 133 MHz CPU ~1200 MHz)

![133 MHz aida benchmark](https://github.com/rustyJ4ck/EeePC701/blob/main/docs/images/cachemem_133.jpg?raw=true)