# Transhot MVP

Windows에서 이미지 1장을 선택해 OCR 텍스트를 한국어로 번역한 뒤, 원문 영역을 흰색으로 덮고 번역문을 넣어 `output` 폴더에 저장하는 Python GUI MVP입니다.

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

OpenAI API 키를 환경 변수로 설정합니다.

```powershell
$env:OPENAI_API_KEY="sk-..."
```

## 실행

```powershell
python main.py
```

EasyOCR은 첫 실행 시 모델 파일을 다운로드할 수 있습니다.
