@echo off
set "rwcmd=D:\bin\RwPortableV1.7\Rw.exe /Min /Nologo /Stdout /Command="

REM CALL D:\bin\mchbar-enable.bat

echo. > last_tmngs.txt
%rwcmd%"r32 0xFED14110" >> last_tmngs.txt
%rwcmd%"r32 0xFED14114" >> last_tmngs.txt
%rwcmd%"r32 0xFED14118" >> last_tmngs.txt
%rwcmd%"r32 0xFED14120" >> last_tmngs.txt
