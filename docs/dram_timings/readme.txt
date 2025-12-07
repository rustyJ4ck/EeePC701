Optimized timings for EEE701/900 (Celeron M models)

Install RW Everything 1.7, then change path in .bat files "rwcmd=D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command="

On windows, run: 

CL3\opt_mem_timings_cl3.bat  # if your dram module supports CL3 profile
CL4\opt_mem_timings_cl4.bat  # otherwise


On linux:

Add contents of file "grub2_custom.conf" to /etc/grub.d/40_custom to run fixes on boot.




PS: 

If you install dram stick without DDR2-400/CL3 SPD profile (i.e. DDR2-800 CL6 HYMP125S64CP8-S6), system will force CL4 profile!
Workaround: modify SPD with enabled CL3, or patch bootblock [@see bootblock-force-cl3.png]
