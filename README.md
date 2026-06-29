# Transhot MVP

Windows에서 이미지 1장 또는 ZIP 파일을 선택해 OCR 텍스트를 한국어로 번역한 뒤, 원문 영역을 흰색으로 덮고 번역문을 넣어 `output` 폴더에 저장하는 Python GUI MVP입니다.
처리 진행 상황은 앱 하단의 Processing Log에서 확인할 수 있으며, 작업별 로그 파일은 `logs` 폴더에 저장됩니다.

ZIP 파일을 선택하면 `temp/<timestamp>/input`에 압축을 해제하고 내부 이미지(`jpg`, `jpeg`, `png`, `webp`)를 폴더 구조 그대로 처리한 뒤, `output/Translated_<원본파일명>.zip`으로 다시 저장합니다.

## 설치

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

또는 패키지 개발 모드로 설치할 수 있습니다.

```powershell
pip install -e .
```

OpenAI API 키는 앱의 `API Key` 버튼에서 저장할 수 있습니다. 저장된 값은 `config/settings.json`에 기록되며 Git에는 커밋되지 않습니다.

환경 변수로도 설정할 수 있습니다.

```powershell
$env:OPENAI_API_KEY="sk-..."
```

## 실행

```powershell
python main.py
```

EasyOCR은 첫 실행 시 모델 파일을 다운로드할 수 있습니다.
Windows 한글 경로나 특수문자 경로의 이미지도 안정적으로 처리하도록 Pillow 기반 이미지 로딩을 사용합니다.

## Windows 빌드

PyInstaller로 폴더형 실행 파일을 만들 수 있습니다.

```powershell
.\build_windows.bat
```

빌드가 성공하면 `dist/Transhot/Transhot.exe`가 생성됩니다. `dist/Transhot/Transhot.exe`를 실행해 GUI가 열리는지 확인하세요.

빌드 결과물에는 `config/settings.example.json`이 포함됩니다. 실제 API Key가 저장되는 `config/settings.json`은 Git에 커밋되지 않으며, 빌드 산출물에 포함되지 않습니다.

프로젝트에 `fonts/` 폴더가 있으면 빌드 결과물에도 함께 포함됩니다.
