:loop
@ECHO OFF
termgraph visual.csv --color {blue,red} --stacked --title "Stacked Data" --width 140
timeout /t 60
CLS
goto loop

