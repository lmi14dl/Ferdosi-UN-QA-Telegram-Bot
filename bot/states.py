"""مدیریت وضعیت مکالمه کاربران و مدیران"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class UserState(Enum):
    IDLE = "idle"
    SEARCHING = "searching"
    AI_ASKING = "ai_asking"
    # Admin states
    ADMIN_MENU = "admin_menu"
    ADMIN_ADD_CAT_NAME = "admin_add_cat_name"
    ADMIN_ADD_CAT_PARENT = "admin_add_cat_parent"
    ADMIN_EDIT_CAT = "admin_edit_cat"
    ADMIN_ADD_Q_TEXT = "admin_add_q_text"
    ADMIN_ADD_Q_ANSWER = "admin_add_q_answer"
    ADMIN_ADD_Q_CAT = "admin_add_q_cat"
    ADMIN_EDIT_Q = "admin_edit_q"
    ADMIN_ADD_ADMIN_ID = "admin_add_admin_id"
    ADMIN_CONFIRM_DELETE = "admin_confirm_delete"


@dataclass
class ConversationState:
    state: UserState = UserState.IDLE
    data: Dict[str, Any] = field(default_factory=dict)
    page: int = 1


# حافظه در حال اجرا (برای نسخه اولیه کافی است؛ پس از ریستارت پاک می‌شود)
_states: Dict[int, ConversationState] = {}


def get_state(user_id: int) -> ConversationState:
    if user_id not in _states:
        _states[user_id] = ConversationState()
    return _states[user_id]


def set_state(user_id: int, state: UserState, **data):
    cs = get_state(user_id)
    cs.state = state
    if data:
        cs.data.update(data)


def clear_state(user_id: int):
    _states[user_id] = ConversationState()


def update_data(user_id: int, **kwargs):
    cs = get_state(user_id)
    cs.data.update(kwargs)
