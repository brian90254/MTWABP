# BRIAN COX copyright 2025
#
# SHORTCUT SCRIPT:
#   runQRcodeGenerator.command
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SOFTWARE/PythonScripts/QRcodeGenerator/
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src" AND PASS HTML LINK ARGUMENTS
#   python src/QRcodeGenerator_1.py "https://example.com/page1"
# ----------------------------

import qrcode

# url = "https://bit.ly/MTWABP1"  # use shortened URL
# http://www.space-eight.com/PortalMindMap_MTWABP_1.html
# url = "https://www.space-eight.com/PINBALL.html"  # use shortened URL
# url = "http://www.space-eight.com/PortalMindMap_MTWABP_1.html"
# url = "https://www.youtube.com/playlist?list=PLdSfbvcZ5Bcb5yycEkbfaCs9yi-xZtaS0"
url = "https://www.youtube.com/playlist?list=PLdSfbvcZ5BcacgBrc7qFDFsXvZhY3QDL0"

qr = qrcode.QRCode(
    version=1,  # smallest grid size
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=1,  # pixel size per box
    border=2,
)
qr.add_data(url)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("OUTPUT/simplified_qr.png")
