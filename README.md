# Transhot MVP

Windows에서 이미지 1장 또는 ZIP 파일을 선택해 OCR 텍스트를 한국어로 번역한 뒤, 원문 영역을 흰색으로 덮고 번역문을 넣어 원본 파일과 같은 폴더에 저장하는 Python GUI MVP입니다.
처리 진행 상황은 앱 하단의 Processing Log에서 확인할 수 있으며, 작업별 로그 파일은 `logs` 폴더에 저장됩니다.

ZIP 파일을 선택하면 `temp/<timestamp>/input`에 압축을 해제하고 내부 이미지(`jpg`, `jpeg`, `png`, `webp`)를 폴더 구조 그대로 처리한 뒤, 원본 ZIP과 같은 폴더에 `re_<원본파일명>.zip`으로 다시 저장합니다.
이미지 결과도 원본 이미지와 같은 폴더에 `re_<원본파일명>` 형식으로 저장되며, 같은 이름이 있으면 `_1`, `_2` 번호가 자동으로 붙습니다.

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
같은 설정 창에서 번역 엔진을 `Google Free Test` 또는 `OpenAI`로 선택할 수 있습니다.

`Google Free Test`는 API Key 없이 빠른 테스트용으로 사용할 수 있습니다. 공식 Google Cloud Translation API가 아니므로 안정성을 보장하지 않습니다. 정식 사용/배포 단계에서는 OpenAI 또는 공식 번역 API 사용을 권장합니다.

환경 변수로도 설정할 수 있습니다.

```powershell
$env:OPENAI_API_KEY="sk-..."
```

## 실행

```powershell
python main.py
```

`이미지 선택 및 번역` 버튼으로 파일을 고르거나, 앱 화면에 이미지/ZIP 파일을 드래그앤드랍해서 바로 처리를 시작할 수 있습니다. 여러 파일을 동시에 드롭하면 첫 번째 지원 파일만 처리합니다.

EasyOCR은 첫 실행 시 모델 파일을 다운로드할 수 있습니다.
Windows 한글 경로나 특수문자 경로의 이미지도 안정적으로 처리하도록 Pillow 기반 이미지 로딩을 사용합니다.
OCR에서 추출된 한글, 일본어, 중국어 등 Unicode 텍스트가 번역 단계에서 안전하게 전달되도록 처리합니다.

## Windows 빌드

PyInstaller로 폴더형 실행 파일을 만들 수 있습니다.

```powershell
.\build_windows.bat
```

빌드가 성공하면 `dist/Transhot/Transhot.exe`가 생성됩니다. `dist/Transhot/Transhot.exe`를 실행해 GUI가 열리는지 확인하세요.

빌드 결과물에는 `config/settings.example.json`이 포함됩니다. 실제 API Key가 저장되는 `config/settings.json`은 Git에 커밋되지 않으며, 빌드 산출물에 포함되지 않습니다.

프로젝트에 `fonts/` 폴더가 있으면 빌드 결과물에도 함께 포함됩니다.
