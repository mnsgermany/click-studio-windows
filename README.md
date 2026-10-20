# Click Studio для Windows

Та же программа, что на Mac: madmom находит доли и сильную долю, клик повторяет все ускорения и замедления песни
(с починкой срывов вторым, ровным проходом). Движок `engine/click_engine.py` — тот же файл, что в Mac-версии;
отличается только чтение M4A/AAC/видео (на Windows через встроенные библиотеки FFmpeg из PyAV).

## Установка
`ClickStudio-Setup-<версия>.exe` — полностью офлайн: Python, madmom, Qt и FFmpeg внутри, интернет не нужен.
Windows 10/11, 64 бит.

## Лицензия
Как на Mac: `ClickStudio-1|<e-mail>|<код компьютера>`, RSA PKCS#1 v1.5 + SHA-256, ключ в base64.
Код компьютера: первые 16 hex от SHA-256(`clickstudio|uuid:<SMBIOS UUID>`), запасные `guid:<MachineGuid>`, `host:<имя>`.
Без лицензии всё работает 5 минут после каждого запуска, потом «Слушать» и «Сохранить» открывают окно «Лицензия…».
Файл запроса `.csreq`. Служебные флаги: `"Click Studio.exe" --machine-code`, `--check-license email key [code]`.
Лицензия хранится в `%APPDATA%\Click Studio\license.json`, кеш анализа — в `%LOCALAPPDATA%\Click Studio\cache`.

## Сборка
GitHub Actions (`.github/workflows/build.yml`) на Windows: зависимости → тесты лицензии и движка → PyInstaller →
проверка собранного движка → Inno Setup → тихая установка и проверка установленного движка.
Установщик — в артефактах сборки; при теге `v*` — в Releases.

Локально (Windows, Python 3.12, Visual Studio Build Tools):
```
pip install -r requirements.txt
pip install --no-build-isolation -r requirements-madmom.txt
python app/main.py                      # запуск из исходников
pyinstaller --noconfirm ClickStudio.spec
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer\ClickStudio.iss
```
