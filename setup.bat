rem git lfs install
rem git lfs pull
rem py --list
py -3.13 -m venv virt
"virt/Scripts/activate.bat"
python.exe -m pip install --upgrade pip
pip install -r requirements.txt