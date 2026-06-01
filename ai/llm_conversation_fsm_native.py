"""Conversation State Machine — Structured conversation flow, forms, and guided interactions.

Modul ini menyediakan:
- StateNode untuk merepresentasikan state dalam conversation
- TransitionRule untuk conditional state transitions
- StateMachine untuk mengeksekusi conversation flow
- FormBuilder untuk structured data collection
- ConversationContext untuk menyimpan state, variables, dan history
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class StateType(Enum):
    START = auto()
    QUESTION = auto()
    INPUT = auto()
    VALIDATION = auto()
    PROCESSING = auto()
    RESPONSE = auto()
    BRANCH = auto()
    FORM = auto()
    END = auto()


class TransitionTrigger(Enum):
    USER_INPUT = auto()
    VALIDATION_PASS = auto()
    VALIDATION_FAIL = auto()
    TIMEOUT = auto()
    ERROR = auto()
    CUSTOM = auto()


@dataclass
class StateNode:
    """Single state in a conversation flow."""
    state_id: str
    name: str
    state_type: StateType
    message: str = ""
    action: Optional[Callable[[ConversationContext], Any]] = None
    validator: Optional[Callable[[str, ConversationContext], Tuple[bool, str]]] = None
    transitions: List[TransitionRule] = field(default_factory=list)
    timeout: float = 300.0
    retries: int = 0

    def add_transition(self, target: str, trigger: TransitionTrigger, condition: Optional[Callable[[ConversationContext], bool]] = None) -> StateNode:
        self.transitions.append(TransitionRule(target, trigger, condition))
        return self


@dataclass
class TransitionRule:
    """Transition from one state to another."""
    target_state: str
    trigger: TransitionTrigger
    condition: Optional[Callable[[ConversationContext], bool]] = None


@dataclass
class FormField:
    """Field in a form."""
    field_id: str
    label: str
    field_type: str = "text"  # text, number, email, choice, boolean
    required: bool = True
    options: List[str] = field(default_factory=list)
    validator: Optional[Callable[[str], Tuple[bool, str]]] = None
    value: Any = None


class FormBuilder:
    """Build structured forms for data collection."""

    def __init__(self, form_id: str, name: str):
        self.form_id = form_id
        self.name = name
        self._fields: List[FormField] = []
        self._current_index = 0

    def add_field(self, field: FormField) -> FormBuilder:
        self._fields.append(field)
        return self

    def get_next_question(self) -> Optional[str]:
        if self._current_index < len(self._fields):
            field = self._fields[self._current_index]
            if field.field_type == "choice" and field.options:
                options_str = ", ".join(f"{i+1}. {opt}" for i, opt in enumerate(field.options))
                return f"{field.label}\nOptions: {options_str}"
            return field.label
        return None

    def submit_answer(self, value: str) -> Tuple[bool, Optional[str]]:
        if self._current_index >= len(self._fields):
            return False, "Form already complete"
        field = self._fields[self._current_index]
        # Validate
        if field.validator:
            valid, msg = field.validator(value)
            if not valid:
                return False, msg
        field.value = value
        self._current_index += 1
        return True, None

    def is_complete(self) -> bool:
        return self._current_index >= len(self._fields)

    def get_values(self) -> Dict[str, Any]:
        return {f.field_id: f.value for f in self._fields}

    def get_missing(self) -> List[str]:
        return [f.field_id for f in self._fields if f.required and f.value is None]

    def reset(self) -> None:
        self._current_index = 0
        for f in self._fields:
            f.value = None


class ConversationContext:
    """Runtime context for a conversation session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.variables: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.current_state: str = ""
        self.start_time = time.time()
        self.last_activity = time.time()
        self.form_data: Optional[FormBuilder] = None
        self._retry_count = 0

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value
        self.last_activity = time.time()

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content, "timestamp": time.time()})
        self.last_activity = time.time()

    def record_transition(self, from_state: str, to_state: str, trigger: str) -> None:
        self.history.append({"type": "transition", "from": from_state, "to": to_state, "trigger": trigger, "timestamp": time.time()})

    def is_idle(self, timeout: float = 300.0) -> bool:
        return time.time() - self.last_activity > timeout

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_state": self.current_state,
            "variables": self.variables,
            "history_count": len(self.history),
            "duration": time.time() - self.start_time,
        }


class StateMachine:
    """Execute conversation state machine."""

    def __init__(self):
        self._states: Dict[str, StateNode] = {}
        self._sessions: Dict[str, ConversationContext] = {}

    def add_state(self, state: StateNode) -> StateMachine:
        self._states[state.state_id] = state
        return self

    def create_session(self, session_id: Optional[str] = None) -> ConversationContext:
        sid = session_id or str(uuid.uuid4())[:12]
        ctx = ConversationContext(sid)
        self._sessions[sid] = ctx
        return ctx

    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        return self._sessions.get(session_id)

    def start(self, session_id: str, start_state: str = "start") -> Optional[str]:
        ctx = self._sessions.get(session_id)
        if not ctx:
            return None
        ctx.current_state = start_state
        return self._execute_state(ctx, start_state)

    def process_input(self, session_id: str, user_input: str) -> Optional[str]:
        ctx = self._sessions.get(session_id)
        if not ctx:
            return None

        ctx.add_message("user", user_input)
        current = self._states.get(ctx.current_state)
        if not current:
            return None

        # Check if in form mode
        if ctx.form_data and not ctx.form_data.is_complete():
            valid, error = ctx.form_data.submit_answer(user_input)
            if not valid:
                return error
            if ctx.form_data.is_complete():
                # Form complete, transition
                ctx.set("form_values", ctx.form_data.get_values())
                ctx.form_data = None
                return self._transition(ctx, current, TransitionTrigger.USER_INPUT)
            return ctx.form_data.get_next_question()

        # Validate input if validator exists
        if current.validator:
            valid, error = current.validator(user_input, ctx)
            if not valid:
                ctx._retry_count += 1
                if ctx._retry_count > current.retries:
                    return self._transition(ctx, current, TransitionTrigger.ERROR)
                return error

        ctx.set("last_input", user_input)
        ctx._retry_count = 0
        return self._transition(ctx, current, TransitionTrigger.USER_INPUT)

    def _execute_state(self, ctx: ConversationContext, state_id: str) -> Optional[str]:
        state = self._states.get(state_id)
        if not state:
            return None
        ctx.current_state = state_id

        if state.action:
            state.action(ctx)

        if state.state_type == StateType.END:
            return state.message or "Conversation ended."

        if state.state_type == StateType.FORM and state.message:
            # Initialize form
            form = FormBuilder(f"form-{state_id}", state.name)
            # Parse form fields from message (simplified)
            ctx.form_data = form
            return form.get_next_question() or state.message

        return state.message

    def _transition(self, ctx: ConversationContext, current: StateNode, trigger: TransitionTrigger) -> Optional[str]:
        for trans in current.transitions:
            if trans.trigger == trigger:
                if trans.condition is None or trans.condition(ctx):
                    ctx.record_transition(current.state_id, trans.target_state, trigger.name)
                    return self._execute_state(ctx, trans.target_state)
        # Default: stay in current state if no matching transition
        return current.message

    def get_session_count(self) -> int:
        return len(self._sessions)

    def cleanup_idle(self, timeout: float = 300.0) -> int:
        to_remove = [sid for sid, ctx in self._sessions.items() if ctx.is_idle(timeout)]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CONVERSATION STATE MACHINE DEMO")
    print("=" * 70)

    sm = StateMachine()

    # Build a support ticket flow
    sm.add_state(StateNode("start", "Greeting", StateType.START, "Welcome to support! What can I help you with?"))
    sm.add_state(StateNode("ask_category", "Category", StateType.QUESTION, "Please choose a category: 1. Technical 2. Billing 3. General"))
    sm.add_state(StateNode("technical_form", "Technical Form", StateType.FORM, "Technical issue form"))
    sm.add_state(StateNode("billing_form", "Billing Form", StateType.FORM, "Billing issue form"))
    sm.add_state(StateNode("process", "Processing", StateType.PROCESSING, "Processing your request..."))
    sm.add_state(StateNode("response", "Response", StateType.RESPONSE, "Thank you! Your ticket has been created."))
    sm.add_state(StateNode("end", "End", StateType.END, "Goodbye!"))

    # Transitions
    sm._states["start"].add_transition("ask_category", TransitionTrigger.USER_INPUT)
    sm._states["ask_category"].add_transition("technical_form", TransitionTrigger.USER_INPUT, lambda ctx: ctx.get("last_input") == "1")
    sm._states["ask_category"].add_transition("billing_form", TransitionTrigger.USER_INPUT, lambda ctx: ctx.get("last_input") == "2")
    sm._states["ask_category"].add_transition("process", TransitionTrigger.USER_INPUT, lambda ctx: ctx.get("last_input") == "3")
    sm._states["technical_form"].add_transition("process", TransitionTrigger.USER_INPUT)
    sm._states["billing_form"].add_transition("process", TransitionTrigger.USER_INPUT)
    sm._states["process"].add_transition("response", TransitionTrigger.USER_INPUT)
    sm._states["response"].add_transition("end", TransitionTrigger.USER_INPUT)

    # 1. Create session
    print("\n[1] Create Session")
    ctx = sm.create_session()
    print(f"  Session: {ctx.session_id}")

    # 2. Start conversation
    print("\n[2] Start Conversation")
    msg = sm.start(ctx.session_id, "start")
    print(f"  Bot: {msg}")

    # 3. User selects category
    print("\n[3] User Input - Category")
    msg = sm.process_input(ctx.session_id, "1")
    print(f"  Bot: {msg}")

    # 4. Form handling (simulated)
    print("\n[4] Form Handling")
    form = FormBuilder("ticket-form", "Support Ticket")
    form.add_field(FormField("issue", "Describe your technical issue:"))
    form.add_field(FormField("priority", "Priority (1-High, 2-Medium, 3-Low):", "choice", options=["High", "Medium", "Low"]))
    ctx.form_data = form
    print(f"  Question: {form.get_next_question()}")
    form.submit_answer("My server is down")
    print(f"  Question: {form.get_next_question()}")
    form.submit_answer("1")
    print(f"  Complete: {form.is_complete()}")
    print(f"  Values: {form.get_values()}")

    # 5. Process and end
    print("\n[5] Process Flow")
    msg = sm.process_input(ctx.session_id, "done")
    print(f"  Bot: {msg}")

    # 6. Context inspection
    print("\n[6] Context Inspection")
    print(f"  Session count: {sm.get_session_count()}")
    print(f"  Context: {ctx.to_dict()}")
    print(f"  History entries: {len(ctx.history)}")

    # 7. Validation example
    print("\n[7] Validation Example")
    sm2 = StateMachine()
    sm2.add_state(StateNode(
        "ask_email", "Email Input", StateType.INPUT, "Please enter your email:",
        validator=lambda val, ctx: ("@" in val and "." in val, "Invalid email format")
    ))
    sm2.add_state(StateNode("valid", "Valid", StateType.RESPONSE, "Email valid!"))
    sm2._states["ask_email"].add_transition("valid", TransitionTrigger.VALIDATION_PASS)
    ctx2 = sm2.create_session()
    sm2.start(ctx2.session_id, "ask_email")
    msg = sm2.process_input(ctx2.session_id, "invalid")
    print(f"  Invalid input: {msg}")
    msg = sm2.process_input(ctx2.session_id, "user@example.com")
    print(f"  Valid input: {msg}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()
