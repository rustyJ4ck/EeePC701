
### Overclock EeePC 701/900 linux utility
Bash script to overclock EeePC CPU (Celeron M 353 ULV 900 MHz). Using i2c-dev module to contact PLL chip (root required). Downclock also supported.

Stock laptop should be stable up to around 120 MHz FSB (1080 MHz).
With little bit voltmod you can reach FSB 133 MHz (~1200 Mhz) and even more.

The bad thing is with FSB overclock you also overclock PCIe (FSB > 110 rule PCIe = FSB - 10). Going over PCIe > 120 is not recommended, so safe limit for FSB is around 130 MHz. But with FSB that high overheating becomes the main problem. Tiny fan can't handle that much heat.

FSB 121MHz  ~30 min stress:  Temp: 67 Fan: 2470 (%80)

Example: To overclock FSB to 121 MHz (CPU 1089 MHz) run

`./oc-run.sh 121`

```
--- FSB 121 MHz validated. Starting Overclock ---
NOTICE: i2c-dev interface not found. Attempting to load module...
SUCCESS: i2c-dev loaded.
=== Eee PC 701/900 Overclocking Tool ===
Starting Frequency: 100.00 MHz | Target: 121 MHz
Applied: CPU 909 MHz | FSB 101.00 MHz (M:24 N:101) | PCIe 100 MHz (M:24 N:100)
Applied: CPU 927 MHz | FSB 103.00 MHz (M:24 N:103) | PCIe 100 MHz (M:24 N:100)
Applied: CPU 945 MHz | FSB 105.00 MHz (M:24 N:105) | PCIe 100 MHz (M:24 N:100)
Applied: CPU 963 MHz | FSB 107.00 MHz (M:24 N:107) | PCIe 100 MHz (M:24 N:100)
Applied: CPU 981 MHz | FSB 109.00 MHz (M:24 N:109) | PCIe 103 MHz (M:36 N:154.5)
Applied: CPU 999 MHz | FSB 111.00 MHz (M:24 N:111) | PCIe 103 MHz (M:36 N:154.5)
Applied: CPU 1017 MHz | FSB 113.00 MHz (M:24 N:113) | PCIe 106 MHz (M:36 N:159)
Applied: CPU 1035 MHz | FSB 115.00 MHz (M:24 N:115) | PCIe 106 MHz (M:36 N:159)
Applied: CPU 1053 MHz | FSB 117.00 MHz (M:24 N:117) | PCIe 109 MHz (M:36 N:163.5)
Applied: CPU 1071 MHz | FSB 119.00 MHz (M:24 N:119) | PCIe 112 MHz (M:36 N:168)
Applied: CPU 1089 MHz | FSB 121.00 MHz (M:24 N:121) | PCIe 112 MHz (M:36 N:168)
```
To revert overclocking (or underclock cpu) choose target FSB lower than current

`$ ./oc_run.sh 85`

**Benchmarks:** see utils/ folder

Opengl benchmark (FPS) 

`$ ./utils/glxgears.sh ` 

```
CPU 900.00 MHz  | FSB 100.00 MHz  >  1066 frames in 5.0 seconds = 213.040 FPS
CPU 990.00 MHz  | FSB 110.00 MHz  >  1181 frames in 5.0 seconds = 236.119 FPS
CPU 1080.00 MHz | FSB 120.00 MHz  >  1279 frames in 5.0 seconds = 255.671 FPS
```

**See also**

Tightest possible timings to improve latency: bash script *[DRAM_CL3_optimized.sh](https://github.com/rustyJ4ck/EeePC701/tree/main/docs/dram_timings/linux/opt_mem_timings_cl3.sh)* 
or config for grub  *[DRAM_CL3_grub.conf](https://github.com/rustyJ4ck/EeePC701/tree/main/docs/dram_timings/grub2_custom.conf)* 

Fixes for intel graphics *[intel_regfix.sh](https://github.com/rustyJ4ck/EeePC701/tree/main/docs/igd_reg_fix/regfix.sh)* 

EeePC  701/900 *[CPU Voltmod](https://github.com/rustyJ4ck/EeePC701/tree/main/docs/voltmod_cpu)* 

Aida memory benchmark (FSB 133 MHz CPU ~1200 MHz)
![133 MHz aida benchmark](https://github.com/rustyJ4ck/EeePC701/blob/main/docs/fsb_overclock/1200mhz-fsb-133-pcie-121_940mv_stock_timings.png?raw=true)