@echo off
set "rwcmd=D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command="

CALL ..\mchbar-enable.bat

%rwcmd%"w32 0xFED14110 0x87FD1064"
%rwcmd%"w32 0xFED14114 0x02609A11"
%rwcmd%"w32 0xFED14118 0x80000150"
%rwcmd%"w32 0xFED14120 0x60000906"  

:: confirm
rem sleep 1
%rwcmd%"r32 0xFED14114
