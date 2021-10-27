cd YOUR PATH
python main_for_bat.py
:loop
@ECHO OFF
termgraph visual.csv --color {blue,red} --stacked --title "Stacked Data" --width 140
timeout /t 60
CLS
goto loop

