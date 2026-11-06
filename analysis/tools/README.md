# asar.py — 从 DSH 桌面应用包中只读取文件

用途：本地 DSH 桌面应用把全部代码打包在
`/Applications/DeepSeek Harness.app/Contents/Resources/app.asar`（单文件）。
本脚本只读解析该归档，用于查阅平台 API 文档（各包 README.md）与实现。

用法：
    python3 analysis/tools/asar.py ls   /dsh/node_modules/@deepseek-ai/dsh-tools
    python3 analysis/tools/asar.py get  /dsh/node_modules/@deepseek-ai/dsh-tools/README.md
    python3 analysis/tools/asar.py find dsh-skill

注意：本地应用版本是 0.2.2-rc.1，而预装 pec 插件声明的是 @deepseek-ai/dsh-tools 0.2.1-rc.2。
只把本仓库当“同族文档”参考，结论要标注版本差异，考场以实际安装包为准。
