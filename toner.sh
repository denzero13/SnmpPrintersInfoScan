#!/bin/bash
while :
do
    termgraph visual.csv --color {blue,red} --stacked --title "Stacked Data" --width 140
    sleep 30
    clear
done