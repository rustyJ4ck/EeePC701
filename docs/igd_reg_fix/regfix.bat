@echo off
set "rwcmd=D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command="

%rwcmd%"w32 0xF7F0209C 0x00400240"
%rwcmd%"w32 0xF7F02120 0x02006A20"
%rwcmd%"w32 0xF7F02124 0x02000180"

:: confirm
sleep 1
%rwcmd%"r32 0xF7F02120

