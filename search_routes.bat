@echo off
cd /d "D:\python\dmx\cdtest\用例初始化构建(2)\5-代码\sc\src"
findstr /s /i "source-manage" *.ts *.tsx 2>nul
findstr /s /i "ai-replica" *.ts *.tsx 2>nul
findstr /s /i "sourceManage" *.ts *.tsx 2>nul
findstr /s /i "aiReplica" *.ts *.tsx 2>nul
echo ---routes---
findstr /s /i "source-manage" config\routes.ts 2>nul
findstr /s /i "ai-replica" config\routes.ts 2>nul
