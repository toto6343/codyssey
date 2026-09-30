import json
import threading
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import settings
from app.services.errors import ConfigError

_db = None
_lock = threading.Lock()
_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_credentials():
    raw = settings.firebase_credentials.strip()
    if not raw:
        raise ConfigError("서버 설정 오류: FIREBASE_SERVICE_ACCOUNT_JSON이 설정되지 않았어요.")
    if raw.startswith("{"):
        try:
            return credentials.Certificate(json.loads(raw))
        except json.JSONDecodeError as e:
            raise ConfigError("서버 설정 오류: FIREBASE_SERVICE_ACCOUNT_JSON의 JSON이 깨져 있어요.") from e
        except ValueError as e:
            raise ConfigError("서버 설정 오류: 서비스 계정 키 내용이 올바르지 않아요.") from e
    path = Path(raw)
    path = path if path.is_absolute() else _BACKEND_DIR / path  # 상대경로는 backend/ 기준
    if not path.exists():
        raise ConfigError("서버 설정 오류: 서비스 계정 키 파일을 찾을 수 없어요.")
    return credentials.Certificate(str(path))


def get_db():
    """Firestore 클라이언트를 처음 필요할 때 한 번만 생성한다 (스레드 안전)."""
    global _db
    if _db is not None:
        return _db
    with _lock:
        if _db is None:
            try:
                app = firebase_admin.get_app()          # 이미 초기화돼 있으면 재사용
            except ValueError:
                app = firebase_admin.initialize_app(_load_credentials())
            _db = firestore.client(app)
    return _db