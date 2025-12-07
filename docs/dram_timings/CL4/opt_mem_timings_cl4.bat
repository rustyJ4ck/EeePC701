@echo off
set "rwcmd=D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command="

CALL ..\mchbar-enable.bat

rem FSB106 CL4 Profile

%rwcmd%"w32 0xFED14110 0x88BC10D8"
%rwcmd%"w32 0xFED14114 0x03408110"
%rwcmd%"w32 0xFED14118 0x80000150"
%rwcmd%"w32 0xFED14120 0x40000906"

:: confirm
rem sleep 1
%rwcmd%"r32 0xFED14114
