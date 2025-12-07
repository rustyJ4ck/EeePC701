@echo off
set "rwcmd=D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command="

rem CALL D:\bin\mchbar-enable.bat

%rwcmd%"w32 0xFED14110 0x987820C8"
%rwcmd%"w32 0xFED14114 0x0290D211"
%rwcmd%"w32 0xFED14118 0x80000230"
%rwcmd%"w32 0xFED14120 0x40000A06"

:: confirm

rem sleep 1
%rwcmd%"r32 0xFED14114
