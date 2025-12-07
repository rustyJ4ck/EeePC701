@echo off

set "rwcmd=D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command="

%rwcmd%"wpci32 0 0 0 54h 0xB8000019"

rem set setpci=D:\bin\pciutils-3.5.5-win32\setpci.exe

:: 27 EPBAR
:: 28 MCHBAR
:: 29 DMIBAR
:: 31 PCIEXBAR

REM >p printf ^%X bindec('10111000000000000000000000011001')
REM B8000019

:: deven 0x90000019 <- only MCHBAR

rem %setpci% -s 00:00.0 54.L=0xB8000019
rem %setpci% -s 00:00.0 54.L

:: 0xFED14000
rem %setpci% -s 00:00.0 44.L 

