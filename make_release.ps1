# Cleanup
Remove-Item -Force -Recurse build
Remove-Item -Force -Recurse dist
Remove-Item -Force Lunii*.msi
Remove-Item -Force Lunii*_portable.zip

# msi build
..\lunii-venv\Scripts\python.exe .\setup.py build_exe
tools\rcedit-x64.exe build\exe.win-amd64-3.11\Lunii-Qt.exe --set-icon res\lunii.ico
..\lunii-venv\Scripts\python.exe .\setup.py bdist_msi

# prep for zip
move build\exe.win-amd64-3.11 "build\Lunii Qt"
# MSI & portable zip
move dist\*.msi .
Compress-Archive -DestinationPath Lunii.Qt-win64_portable.zip -CompressionLevel Optimal -Path "build\Lunii Qt"