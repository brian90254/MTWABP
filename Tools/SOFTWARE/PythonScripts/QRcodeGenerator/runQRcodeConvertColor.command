#!/bin/bash
cd Dropbox/GitHub/MTWABP/Tools/SOFTWARE/PythonScripts/QRcodeGenerator/

source venv39/bin/activate

python src/QRcodeConvertColor_3.py --input OUTPUT/simplified_qr_4.png --output OUTPUT/simplified_qr_4D_color.png --ring-width 4 --center auto