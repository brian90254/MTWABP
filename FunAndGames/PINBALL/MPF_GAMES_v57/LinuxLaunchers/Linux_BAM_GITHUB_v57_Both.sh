#!/bin/bash

#ACTIVATE VIRTUAL ENVIRONMENT
source ~/venvs/PY311_MPF057/bin/activate

# SET MAIN GAME DIRECTORY
cd Dropbox/GitHub/MTWABP/FunAndGames/PINBALL/MPF_GAMES_v57/

# GOTO SPECIFIC GAME FOLDER
#cd BAM_EVEL_KNIEVEL_v57/
cd BAM_TOTEM_v57/

sleep 2s
mpf both -xvVaA
#mpf both -vVaA
#mpf both
