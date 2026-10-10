"""
Per-user RAGSystem cache.
Each user gets one RAGSystem instance (initialised once, reused across requests).
"""
from threading import Lock
from fastapi import Depends

from auth.models import User
from auth.utils import get_current_user
from core.rag_system import RAGSystem

_cache: dict[str, RAGSystem] = {}
_lock = Lock()


def get_rag_system(current_user: User = Depends(get_current_user)) -> RAGSystem:
    user_id = current_user.id
    if user_id not in _cache:
        with _lock:
            if user_id not in _cache:
                system = RAGSystem(user_id=user_id)
                system.initialize()
                _cache[user_id] = system
    return _cache[user_id]
