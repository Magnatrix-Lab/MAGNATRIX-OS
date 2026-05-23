"""
batch_d_frontend_ui_native.py
A pure-Python frontend/UI/portfolio HTML/CSS/JS string generator.
Consolidates patterns from 11+ frontend/UI/portfolio repositories.
No external template engine — all output built via f-strings & string composition.
"""

from __future__ import annotations

import json
import os
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Section 1: UI Component Generators (lines ~1–250)
# =============================================================================

class HTMLComponent(ABC):
    """Abstract base for all HTML-generating components."""

    @abstractmethod
    def render(self) -> str:
        """Return the HTML string representation."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class LoginForm(HTMLComponent):
    """Generate a complete login form with validation attributes and OAuth stubs."""

    def __init__(
        self,
        action: str = "/login",
        method: str = "post",
        remember_me: bool = True,
        forgot_password_url: str = "#forgot",
        oauth_providers: List[str] = field(default_factory=lambda: ["Google", "GitHub"]),
    ) -> None:
        self.action = action
        self.method = method
        self.remember_me = remember_me
        self.forgot_password_url = forgot_password_url
        self.oauth_providers = oauth_providers

    def render(self) -> str:
        remember_block = (
            f"""<div class="form-remember">
                <label><input type="checkbox" name="remember" /> Remember me</label>
                <a href="{self.forgot_password_url}" class="forgot-link">Forgot password?</a>
            </div>"""
            if self.remember_me
            else ""
        )
        oauth_buttons = "\n".join(
            f'<button type="button" class="oauth-btn oauth-{p.lower()}">Sign in with {p}</button>'
            for p in self.oauth_providers
        )
        return textwrap.dedent(
            f"""\
            <form class="login-form" action="{self.action}" method="{self.method}">
                <h2>Sign In</h2>
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required minlength="3" maxlength="32" placeholder="Enter username" />
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required minlength="6" placeholder="Enter password" />
                </div>
                {remember_block}
                <button type="submit" class="btn btn-primary">Sign In</button>
                <div class="oauth-divider"><span>or</span></div>
                <div class="oauth-buttons">
                    {oauth_buttons}
                </div>
            </form>
            """
        )

    def __repr__(self) -> str:
        return (
            f"<LoginForm action={self.action!r} method={self.method!r} "
            f"remember_me={self.remember_me}>"
        )


class CardComponent(HTMLComponent):
    """A card with header, body, footer slots and action buttons."""

    def __init__(
        self,
        header: str = "",
        body: str = "",
        footer: str = "",
        actions: List[Tuple[str, str]] = None,  # (label, url)
    ) -> None:
        self.header = header
        self.body = body
        self.footer = footer
        self.actions = actions or []

    def render(self) -> str:
        actions_html = "\n".join(
            f'<a href="{url}" class="card-action">{label}</a>' for label, url in self.actions
        )
        return textwrap.dedent(
            f"""\
            <div class="card">
                <div class="card-header">{self.header}</div>
                <div class="card-body">{self.body}</div>
                <div class="card-footer">
                    {self.footer}
                    <div class="card-actions">{actions_html}</div>
                </div>
            </div>
            """
        )

    def __repr__(self) -> str:
        return f"<CardComponent header={self.header!r} actions={len(self.actions)}>"


class ModalDialog(HTMLComponent):
    """Modal with overlay, close button and header/body/footer slots."""

    def __init__(
        self,
        modal_id: str = "modal-1",
        trigger_text: str = "Open Modal",
        header: str = "",
        body: str = "",
        footer: str = "",
    ) -> None:
        self.modal_id = modal_id
        self.trigger_text = trigger_text
        self.header = header
        self.body = body
        self.footer = footer

    def render(self) -> str:
        return textwrap.dedent(
            f"""\
            <button class="btn btn-secondary" onclick="document.getElementById('{self.modal_id}').classList.add('active')">{self.trigger_text}</button>
            <div id="{self.modal_id}" class="modal-overlay" onclick="if(event.target===this) this.classList.remove('active')">
                <div class="modal-dialog" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3>{self.header}</h3>
                        <button class="modal-close" onclick="document.getElementById('{self.modal_id}').classList.remove('active')">&times;</button>
                    </div>
                    <div class="modal-body">{self.body}</div>
                    <div class="modal-footer">{self.footer}</div>
                </div>
            </div>
            """
        )

    def __repr__(self) -> str:
        return f"<ModalDialog id={self.modal_id!r}>"


class NavbarComponent(HTMLComponent):
    """Responsive navbar with brand, nav links and mobile hamburger."""

    def __init__(
        self,
        brand: str = "MySite",
        links: List[Tuple[str, str]] = None,
        dropdown_label: str = "More",
        dropdown_links: List[Tuple[str, str]] = None,
    ) -> None:
        self.brand = brand
        self.links = links or [("Home", "#"), ("About", "#about"), ("Contact", "#contact")]
        self.dropdown_label = dropdown_label
        self.dropdown_links = dropdown_links or [("Settings", "#settings"), ("Logout", "#logout")]

    def render(self) -> str:
        nav_links = "\n".join(f'<a href="{href}">{label}</a>' for label, href in self.links)
        dropdown_items = "\n".join(
            f'<a href="{href}">{label}</a>' for label, href in self.dropdown_links
        )
        return textwrap.dedent(
            f"""\
            <nav class="navbar">
                <a class="navbar-brand" href="#">{self.brand}</a>
                <input type="checkbox" id="nav-toggle" class="nav-toggle" />
                <label for="nav-toggle" class="nav-hamburger"><span></span><span></span><span></span></label>
                <div class="nav-links">
                    {nav_links}
                    <div class="nav-dropdown">
                        <span class="drop-label">{self.dropdown_label}</span>
                        <div class="drop-menu">{dropdown_items}</div>
                    </div>
                </div>
            </nav>
            """
        )

    def __repr__(self) -> str:
        return f"<NavbarComponent brand={self.brand!r} links={len(self.links)}>"


class TableComponent(HTMLComponent):
    """Sortable-stub table with striped and hover rows."""

    def __init__(
        self,
        headers: List[str] = None,
        rows: List[List[str]] = None,
        striped: bool = True,
        hover: bool = True,
    ) -> None:
        self.headers = headers or ["#", "Name", "Status", "Action"]
        self.rows = rows or []
        self.striped = striped
        self.hover = hover

    def render(self) -> str:
        cls = "table"
        if self.striped:
            cls += " table-striped"
        if self.hover:
            cls += " table-hover"
        header_cells = "\n".join(f"<th>{h}</th>" for h in self.headers)
        body_rows = "\n".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
            for row in self.rows
        )
        return textwrap.dedent(
            f"""\
            <table class="{cls}">
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{body_rows}</tbody>
            </table>
            <div class="table-pagination">
                <button class="page-prev">&larr; Prev</button>
                <span class="page-info">Page 1 of 1</span>
                <button class="page-next">Next &rarr;</button>
            </div>
            """
        )

    def __repr__(self) -> str:
        return f"<TableComponent rows={len(self.rows)} striped={self.striped}>"


class ButtonVariants:
    """Factory for styled <button> variants."""

    @staticmethod
    def _base(label: str, extra_cls: str = "", attrs: str = "") -> str:
        return f'<button class="btn {extra_cls}" {attrs}>{label}</button>'

    @classmethod
    def primary(cls, label: str, attrs: str = "") -> str:
        return cls._base(label, "btn-primary", attrs)

    @classmethod
    def secondary(cls, label: str, attrs: str = "") -> str:
        return cls._base(label, "btn-secondary", attrs)

    @classmethod
    def danger(cls, label: str, attrs: str = "") -> str:
        return cls._base(label, "btn-danger", attrs)

    @classmethod
    def ghost(cls, label: str, attrs: str = "") -> str:
        return cls._base(label, "btn-ghost", attrs)

    @classmethod
    def outline(cls, label: str, attrs: str = "") -> str:
        return cls._base(label, "btn-outline", attrs)

    @classmethod
    def link(cls, label: str, attrs: str = "") -> str:
        return cls._base(label, "btn-link", attrs)

    def __repr__(self) -> str:
        return "<ButtonVariants factory>"


class InputVariants:
    """Factory for form input HTML with labels, placeholders and error states."""

    @staticmethod
    def _wrap(
        label: str,
        html: str,
        error: str = "",
    ) -> str:
        err = f'<span class="input-error">{error}</span>' if error else ""
        return f'<div class="form-group">\n<label>{label}</label>\n{html}\n{err}\n</div>'

    @classmethod
    def text(cls, name: str, label: str, placeholder: str = "", error: str = "") -> str:
        return cls._wrap(
            label,
            f'<input type="text" name="{name}" placeholder="{placeholder}" />',
            error,
        )

    @classmethod
    def password(cls, name: str, label: str, placeholder: str = "", error: str = "") -> str:
        return cls._wrap(
            label,
            f'<input type="password" name="{name}" placeholder="{placeholder}" />',
            error,
        )

    @classmethod
    def email(cls, name: str, label: str, placeholder: str = "", error: str = "") -> str:
        return cls._wrap(
            label,
            f'<input type="email" name="{name}" placeholder="{placeholder}" />',
            error,
        )

    @classmethod
    def number(cls, name: str, label: str, placeholder: str = "", error: str = "") -> str:
        return cls._wrap(
            label,
            f'<input type="number" name="{name}" placeholder="{placeholder}" />',
            error,
        )

    @classmethod
    def textarea(cls, name: str, label: str, placeholder: str = "", error: str = "") -> str:
        return cls._wrap(
            label,
            f'<textarea name="{name}" placeholder="{placeholder}"></textarea>',
            error,
        )

    @classmethod
    def select(
        cls, name: str, label: str, options: List[Tuple[str, str]], error: str = ""
    ) -> str:
        opts = "\n".join(f'<option value="{val}">{lbl}</option>' for val, lbl in options)
        return cls._wrap(label, f'<select name="{name}">{opts}</select>', error)

    @classmethod
    def checkbox(cls, name: str, label: str, checked: bool = False) -> str:
        chk = " checked" if checked else ""
        return f'<label class="inline-check"><input type="checkbox" name="{name}"{chk} /> {label}</label>'

    @classmethod
    def radio(cls, name: str, label: str, value: str, checked: bool = False) -> str:
        chk = " checked" if checked else ""
        return f'<label class="inline-radio"><input type="radio" name="{name}" value="{value}"{chk} /> {label}</label>'

    @classmethod
    def toggle(cls, name: str, label: str, checked: bool = False) -> str:
        chk = " checked" if checked else ""
        return (
            f'<label class="toggle-switch">\n'
            f'  <input type="checkbox" name="{name}"{chk} />\n'
            f'  <span class="toggle-slider"></span> {label}\n</label>'
        )

    @classmethod
    def date(cls, name: str, label: str, error: str = "") -> str:
        return cls._wrap(label, f'<input type="date" name="{name}" />', error)

    @classmethod
    def file(cls, name: str, label: str, error: str = "") -> str:
        return cls._wrap(label, f'<input type="file" name="{name}" />', error)

    def __repr__(self) -> str:
        return "<InputVariants factory>"


class Badge(HTMLComponent):
    """Small label/badge component."""

    def __init__(self, text: str, variant: str = "primary") -> None:
        self.text = text
        self.variant = variant

    def render(self) -> str:
        return f'<span class="badge badge-{self.variant}">{self.text}</span>'

    def __repr__(self) -> str:
        return f"<Badge text={self.text!r} variant={self.variant!r}>"


class Alert(HTMLComponent):
    """Alert banner with optional dismiss button."""

    def __init__(self, message: str, variant: str = "info", dismissible: bool = True) -> None:
        self.message = message
        self.variant = variant
        self.dismissible = dismissible

    def render(self) -> str:
        dismiss = (
            '<button class="alert-close" onclick="this.parentElement.remove()">&times;</button>'
            if self.dismissible
            else ""
        )
        return f'<div class="alert alert-{self.variant}">{self.message}{dismiss}</div>'

    def __repr__(self) -> str:
        return f"<Alert variant={self.variant!r}>"


class Toast(HTMLComponent):
    """Toast notification component."""

    def __init__(self, message: str, variant: str = "info") -> None:
        self.message = message
        self.variant = variant

    def render(self) -> str:
        return (
            f'<div class="toast toast-{self.variant}">\n'
            f'  <span>{self.message}</span>\n'
            f'  <button onclick="this.parentElement.remove()">&times;</button>\n</div>'
        )

    def __repr__(self) -> str:
        return f"<Toast message={self.message!r}>"


class Spinner(HTMLComponent):
    """Loading spinner."""

    def __init__(self, size: str = "md") -> None:
        self.size = size

    def render(self) -> str:
        return f'<div class="spinner spinner-{self.size}"></div>'

    def __repr__(self) -> str:
        return f"<Spinner size={self.size!r}>"


class ProgressBar(HTMLComponent):
    """Progress bar with value and label."""

    def __init__(self, value: int, max_val: int = 100, label: str = "") -> None:
        self.value = value
        self.max_val = max_val
        self.label = label

    def render(self) -> str:
        pct = int((self.value / self.max_val) * 100)
        return (
            f'<div class="progress">\n'
            f'  <div class="progress-bar" style="width:{pct}%"></div>\n'
            f'  <span class="progress-label">{self.label or f"{pct}%"}</span>\n</div>'
        )

    def __repr__(self) -> str:
        return f"<ProgressBar value={self.value}/{self.max_val}>"


class Accordion(HTMLComponent):
    """CSS-only accordion using checkbox hack."""

    def __init__(self, items: List[Tuple[str, str]]) -> None:
        self.items = items

    def render(self) -> str:
        blocks = []
        for idx, (title, content) in enumerate(self.items, 1):
            blocks.append(
                textwrap.dedent(
                    f"""\
                    <div class="accordion-item">
                        <input type="checkbox" id="acc-{idx}" class="acc-toggle" />
                        <label for="acc-{idx}" class="acc-title">{title}</label>
                        <div class="acc-content">{content}</div>
                    </div>
                    """
                )
            )
        return '<div class="accordion">\n' + "\n".join(blocks) + "\n</div>"

    def __repr__(self) -> str:
        return f"<Accordion items={len(self.items)}>"


class Tabs(HTMLComponent):
    """CSS-only tabs using radio buttons."""

    def __init__(self, tabs: List[Tuple[str, str]]) -> None:
        self.tabs = tabs

    def render(self) -> str:
        labels = "\n".join(
            f'<label for="tab-{idx}">{title}</label>' for idx, (title, _) in enumerate(self.tabs, 1)
        )
        contents = "\n".join(
            textwrap.dedent(
                f"""\
                <input type="radio" name="tabs" id="tab-{idx}" class="tab-radio" {"checked" if idx == 1 else ""} />
                <div class="tab-panel">{content}</div>
                """
            )
            for idx, (_, content) in enumerate(self.tabs, 1)
        )
        return (
            f'<div class="tabs">\n<div class="tab-labels">{labels}</div>\n{contents}\n</div>'
        )

    def __repr__(self) -> str:
        return f"<Tabs tabs={len(self.tabs)}>"


# =============================================================================
# Section 2: Form Patterns & Validation (lines ~250–400)
# =============================================================================

class Validator(ABC):
    """Base validator with error message support."""

    @abstractmethod
    def validate(self, value: Any) -> Tuple[bool, str]:
        """Return (is_valid, error_message)."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class RequiredValidator(Validator):
    """Ensure a value is present and non-empty."""

    def __init__(self, message: str = "This field is required.") -> None:
        self.message = message

    def validate(self, value: Any) -> Tuple[bool, str]:
        if value is None or str(value).strip() == "":
            return False, self.message
        return True, ""

    def __repr__(self) -> str:
        return f"<RequiredValidator message={self.message!r}>"


class MinLengthValidator(Validator):
    """Ensure string length >= minimum."""

    def __init__(self, min_length: int, message: str = "") -> None:
        self.min_length = min_length
        self.message = message or f"Must be at least {min_length} characters."

    def validate(self, value: Any) -> Tuple[bool, str]:
        if len(str(value)) < self.min_length:
            return False, self.message
        return True, ""

    def __repr__(self) -> str:
        return f"<MinLengthValidator min={self.min_length}>"


class MaxLengthValidator(Validator):
    """Ensure string length <= maximum."""

    def __init__(self, max_length: int, message: str = "") -> None:
        self.max_length = max_length
        self.message = message or f"Must be at most {max_length} characters."

    def validate(self, value: Any) -> Tuple[bool, str]:
        if len(str(value)) > self.max_length:
            return False, self.message
        return True, ""

    def __repr__(self) -> str:
        return f"<MaxLengthValidator max={self.max_length}>"


class RegexValidator(Validator):
    """Validate with a regular expression."""

    def __init__(self, pattern: str, message: str = "Invalid format.") -> None:
        import re

        self.pattern = re.compile(pattern)
        self.message = message

    def validate(self, value: Any) -> Tuple[bool, str]:
        if not self.pattern.match(str(value)):
            return False, self.message
        return True, ""

    def __repr__(self) -> str:
        return f"<RegexValidator pattern={self.pattern.pattern!r}>"


class EmailValidator(Validator):
    """Simple e-mail format validator."""

    def __init__(self, message: str = "Invalid email address.") -> None:
        import re

        self.pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        self.message = message

    def validate(self, value: Any) -> Tuple[bool, str]:
        if not self.pattern.match(str(value)):
            return False, self.message
        return True, ""

    def __repr__(self) -> str:
        return "<EmailValidator>"


class NumberRangeValidator(Validator):
    """Ensure numeric value falls within range."""

    def __init__(
        self, min_val: Optional[float] = None, max_val: Optional[float] = None, message: str = ""
    ) -> None:
        self.min_val = min_val
        self.max_val = max_val
        self.message = message or f"Must be between {min_val} and {max_val}."

    def validate(self, value: Any) -> Tuple[bool, str]:
        try:
            num = float(value)
        except (ValueError, TypeError):
            return False, "Must be a number."
        if self.min_val is not None and num < self.min_val:
            return False, self.message
        if self.max_val is not None and num > self.max_val:
            return False, self.message
        return True, ""

    def __repr__(self) -> str:
        return f"<NumberRangeValidator min={self.min_val} max={self.max_val}>"


@dataclass
class FormField:
    """Declarative field descriptor for form building."""

    name: str
    label: str
    field_type: str = "text"
    required: bool = False
    validators: List[Validator] = field(default_factory=list)
    error_message: str = ""
    placeholder: str = ""
    options: List[Tuple[str, str]] = field(default_factory=list)  # for select/radio

    def __repr__(self) -> str:
        return f"<FormField name={self.name!r} type={self.field_type!r}>"


class FormBuilder:
    """Build a complete HTML form from a declarative field list."""

    def __init__(self, action: str = "#", method: str = "post", fields: List[FormField] = None) -> None:
        self.action = action
        self.method = method
        self.fields = fields or []

    def render(self) -> str:
        inputs = []
        for f in self.fields:
            validators_attr = " ".join(
                f'data-validator="{v.__class__.__name__}"' for v in f.validators
            )
            required_attr = 'required' if f.required else ''
            error_html = f'<span class="field-error">{f.error_message}</span>' if f.error_message else ""

            if f.field_type == "select":
                opts = "\n".join(f'<option value="{val}">{lbl}</option>' for val, lbl in f.options)
                inp = f'<select name="{f.name}" {required_attr}>{opts}</select>'
            elif f.field_type == "textarea":
                inp = f'<textarea name="{f.name}" placeholder="{f.placeholder}" {required_attr}></textarea>'
            elif f.field_type in ("checkbox", "radio"):
                opts = "\n".join(
                    f'<label><input type="{f.field_type}" name="{f.name}" value="{val}" /> {lbl}</label>'
                    for val, lbl in f.options
                )
                inp = f'<div class="field-group">{opts}</div>'
            else:
                inp = f'<input type="{f.field_type}" name="{f.name}" placeholder="{f.placeholder}" {required_attr} {validators_attr} />'

            inputs.append(
                f'<div class="form-group{" form-error" if f.error_message else ""}">\n'
                f'  <label for="{f.name}">{f.label}</label>\n'
                f'  {inp}\n'
                f'  {error_html}\n'
                f'</div>'
            )

        return (
            f'<form class="generated-form" action="{self.action}" method="{self.method}">\n'
            + "\n".join(inputs)
            + '\n<button type="submit" class="btn btn-primary">Submit</button>\n</form>'
        )

    def __repr__(self) -> str:
        return f"<FormBuilder fields={len(self.fields)}>"


class FormRenderer:
    """Render a form with inline validation, error styling and success state."""

    def __init__(self, builder: FormBuilder) -> None:
        self.builder = builder
        self.errors: Dict[str, str] = {}
        self.success = False

    def validate(self, data: Dict[str, Any]) -> bool:
        self.errors.clear()
        for field in self.builder.fields:
            value = data.get(field.name, "")
            for v in field.validators:
                ok, msg = v.validate(value)
                if not ok:
                    self.errors[field.name] = msg
                    break
        return len(self.errors) == 0

    def render(self, data: Dict[str, Any] = None) -> str:
        data = data or {}
        parts = []
        for field in self.builder.fields:
            err = self.errors.get(field.name, "")
            val = data.get(field.name, "")
            cls = "form-group"
            if err:
                cls += " has-error"
            err_span = f'<span class="inline-error">{err}</span>' if err else ""
            parts.append(
                f'<div class="{cls}">\n'
                f'  <label>{field.label}</label>\n'
                f'  <input type="{field.field_type}" name="{field.name}" value="{val}" />\n'
                f'  {err_span}\n'
                f'</div>'
            )
        success_banner = '<div class="form-success">Form submitted successfully!</div>' if self.success else ""
        return (
            f'<form class="rendered-form" action="{self.builder.action}" method="{self.builder.method}">\n'
            f'{success_banner}\n'
            + "\n".join(parts)
            + '\n<button type="submit" class="btn btn-primary">Submit</button>\n</form>'
        )

    def __repr__(self) -> str:
        return f"<FormRenderer errors={len(self.errors)} success={self.success}>"


class FormState:
    """Track dirty/pristine, touched, valid/invalid per field."""

    def __init__(self, field_names: List[str]) -> None:
        self.fields = {name: {"dirty": False, "touched": False, "valid": True} for name in field_names}

    def mark_dirty(self, name: str) -> None:
        self.fields[name]["dirty"] = True

    def mark_touched(self, name: str) -> None:
        self.fields[name]["touched"] = True

    def set_valid(self, name: str, valid: bool) -> None:
        self.fields[name]["valid"] = valid

    @property
    def overall_valid(self) -> bool:
        return all(f["valid"] for f in self.fields.values())

    def __repr__(self) -> str:
        return f"<FormState fields={list(self.fields.keys())} valid={self.overall_valid}>"


# =============================================================================
# Section 3: Portfolio Generators (lines ~400–600)
# =============================================================================

@dataclass
class PortfolioConfig:
    """Configuration dataclass for a one-page portfolio."""

    name: str = "Alex Doe"
    title: str = "Full-Stack Developer"
    tagline: str = "I build things for the web."
    bio: str = "Passionate developer with experience across the stack."
    skills: Dict[str, int] = field(default_factory=lambda: {"Python": 90, "JavaScript": 85, "CSS": 80})
    projects: List[Dict[str, str]] = field(
        default_factory=lambda: [
            {"name": "Project Alpha", "desc": "A cool app.", "link": "#"},
            {"name": "Project Beta", "desc": "Another app.", "link": "#"},
        ]
    )
    experience: List[Dict[str, str]] = field(
        default_factory=lambda: [
            {"role": "Developer", "company": "Acme", "years": "2020-2023"},
            {"role": "Intern", "company": "Starter", "years": "2019-2020"},
        ]
    )
    social: Dict[str, str] = field(default_factory=lambda: {"GitHub": "#", "LinkedIn": "#"})
    email: str = "alex@example.com"

    def __repr__(self) -> str:
        return f"<PortfolioConfig name={self.name!r}>"


class ThemeEngine:
    """Generate CSS custom properties for portfolio themes."""

    THEMES: Dict[str, Dict[str, str]] = {
        "minimal": {
            "--bg": "#ffffff",
            "--fg": "#1a1a1a",
            "--primary": "#2563eb",
            "--accent": "#64748b",
            "--font-base": "'Inter', sans-serif",
            "--radius": "4px",
        },
        "dark": {
            "--bg": "#0f172a",
            "--fg": "#e2e8f0",
            "--primary": "#22d3ee",
            "--accent": "#a78bfa",
            "--font-base": "'Inter', sans-serif",
            "--radius": "8px",
        },
        "colorful": {
            "--bg": "#fff7ed",
            "--fg": "#431407",
            "--primary": "#f97316",
            "--accent": "#ec4899",
            "--font-base": "'Poppins', sans-serif",
            "--radius": "12px",
        },
        "professional": {
            "--bg": "#f8fafc",
            "--fg": "#0f172a",
            "--primary": "#1e3a5f",
            "--accent": "#c0a062",
            "--font-base": "'Merriweather', serif",
            "--radius": "2px",
        },
    }

    @classmethod
    def css(cls, theme: str) -> str:
        vars_ = cls.THEMES.get(theme, cls.THEMES["minimal"])
        root = "\n".join(f"  {k}: {v};" for k, v in vars_.items())
        return f":root {{\n{root}\n}}"

    def __repr__(self) -> str:
        return "<ThemeEngine>"


class PortfolioSite(HTMLComponent):
    """Generate a complete one-page portfolio HTML string."""

    def __init__(self, config: PortfolioConfig, theme: str = "minimal") -> None:
        self.config = config
        self.theme = theme

    def render(self) -> str:
        theme_css = ThemeEngine.css(self.theme)
        skills_html = "\n".join(
            f'<div class="skill"><span>{name}</span><div class="skill-bar"><div style="width:{pct}%"></div></div></div>'
            for name, pct in self.config.skills.items()
        )
        projects_html = "\n".join(
            f'<div class="project-card"><h3>{p["name"]}</h3><p>{p["desc"]}</p><a href="{p["link"]}">View</a></div>'
            for p in self.config.projects
        )
        exp_html = "\n".join(
            f'<div class="timeline-item"><h4>{e["role"]}</h4><span>{e["company"]} | {e["years"]}</span></div>'
            for e in self.config.experience
        )
        social_html = "\n".join(
            f'<a href="{url}">{name}</a>' for name, url in self.config.social.items()
        )
        return textwrap.dedent(
            f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>{self.config.name} — Portfolio</title>
                <style>
                {theme_css}
                * {{ margin:0; padding:0; box-sizing:border-box; }}
                body {{ font-family: var(--font-base); background: var(--bg); color: var(--fg); }}
                .container {{ max-width: 960px; margin: 0 auto; padding: 2rem 1rem; }}
                .hero {{ text-align:center; padding: 6rem 1rem; background: linear-gradient(135deg, var(--primary), var(--accent)); color:#fff; }}
                .hero h1 {{ font-size: 3rem; margin-bottom: 0.5rem; }}
                .hero p {{ font-size: 1.25rem; opacity: 0.9; }}
                .hero a.cta {{ display:inline-block; margin-top:1.5rem; padding:0.75rem 1.5rem; background:#fff; color:var(--primary); border-radius:var(--radius); text-decoration:none; font-weight:600; }}
                .section {{ padding: 4rem 1rem; }}
                .section h2 {{ margin-bottom: 1.5rem; color: var(--primary); }}
                .about {{ display:flex; gap:2rem; align-items:center; flex-wrap:wrap; }}
                .about img {{ width:160px; height:160px; border-radius:50%; background:var(--accent); object-fit:cover; }}
                .skills {{ display:grid; gap:1rem; }}
                .skill-bar {{ background:#e2e8f0; border-radius:var(--radius); height:8px; overflow:hidden; }}
                .skill-bar div {{ background:var(--primary); height:100%; }}
                .projects {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(240px,1fr)); gap:1.5rem; }}
                .project-card {{ background:var(--bg); border:1px solid #e2e8f0; border-radius:var(--radius); padding:1.5rem; box-shadow:0 2px 8px rgba(0,0,0,0.04); }}
                .timeline-item {{ border-left:3px solid var(--primary); padding-left:1rem; margin-bottom:1.5rem; }}
                .contact-form {{ display:grid; gap:1rem; max-width:480px; }}
                .contact-form input, .contact-form textarea {{ width:100%; padding:0.75rem; border:1px solid #cbd5e1; border-radius:var(--radius); }}
                footer {{ text-align:center; padding:2rem; border-top:1px solid #e2e8f0; }}
                footer a {{ margin:0 0.5rem; color:var(--primary); text-decoration:none; }}
                @media(max-width:600px){{ .hero h1{{font-size:2rem;}} .about{{flex-direction:column;text-align:center;}} }}
                </style>
            </head>
            <body>
                <section class="hero">
                    <h1>{self.config.name}</h1>
                    <p>{self.config.title} — {self.config.tagline}</p>
                    <a class="cta" href="#contact">Get in Touch</a>
                </section>
                <div class="container">
                    <section class="section" id="about">
                        <h2>About</h2>
                        <div class="about">
                            <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="Photo" />
                            <p>{self.config.bio}</p>
                        </div>
                    </section>
                    <section class="section" id="skills">
                        <h2>Skills</h2>
                        <div class="skills">{skills_html}</div>
                    </section>
                    <section class="section" id="projects">
                        <h2>Projects</h2>
                        <div class="projects">{projects_html}</div>
                    </section>
                    <section class="section" id="experience">
                        <h2>Experience</h2>
                        <div class="timeline">{exp_html}</div>
                    </section>
                    <section class="section" id="contact">
                        <h2>Contact</h2>
                        <form class="contact-form" action="mailto:{self.config.email}" method="post">
                            <input type="text" name="name" placeholder="Your Name" required />
                            <input type="email" name="email" placeholder="Your Email" required />
                            <textarea name="message" rows="4" placeholder="Your Message" required></textarea>
                            <button type="submit" class="btn btn-primary">Send Message</button>
                        </form>
                    </section>
                </div>
                <footer>
                    <p>&copy; {self.config.name}</p>
                    <div class="social">{social_html}</div>
                </footer>
            </body>
            </html>
            """
        )

    def __repr__(self) -> str:
        return f"<PortfolioSite theme={self.theme!r}>"


# =============================================================================
# Section 4: Micro Frontend Patterns (lines ~600–750)
# =============================================================================

class MicroFrontendShell(HTMLComponent):
    """Container layout for micro-frontend architecture."""

    def __init__(
        self,
        header: str = "",
        sidebar: str = "",
        content: str = "",
        footer: str = "",
    ) -> None:
        self.header = header
        self.sidebar = sidebar
        self.content = content
        self.footer = footer

    def render(self) -> str:
        return textwrap.dedent(
            f"""\
            <div class="mfe-shell">
                <header class="mfe-header">{self.header}</header>
                <div class="mfe-body">
                    <aside class="mfe-sidebar">{self.sidebar}</aside>
                    <main class="mfe-content">{self.content}</main>
                </div>
                <footer class="mfe-footer">{self.footer}</footer>
            </div>
            """
        )

    def __repr__(self) -> str:
        return "<MicroFrontendShell>"


class ModuleRegistry:
    """Register micro-apps by name/version with metadata dict."""

    def __init__(self) -> None:
        self._modules: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, version: str, metadata: Dict[str, Any]) -> None:
        self._modules[f"{name}@{version}"] = {"name": name, "version": version, **metadata}

    def get(self, name: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        if version == "latest":
            matches = [m for key, m in self._modules.items() if m["name"] == name]
            return matches[-1] if matches else None
        return self._modules.get(f"{name}@{version}")

    def list(self) -> List[str]:
        return list(self._modules.keys())

    def __repr__(self) -> str:
        return f"<ModuleRegistry modules={len(self._modules)}>"


class ComponentLoader:
    """Stub loader for remote components via iframe or JS module string."""

    @staticmethod
    def iframe(src: str, width: str = "100%", height: str = "400px") -> str:
        return f'<iframe src="{src}" width="{width}" height="{height}" class="remote-component" sandbox="allow-scripts"></iframe>'

    @staticmethod
    def js_module(module_url: str, mount_id: str = "app") -> str:
        return (
            f'<div id="{mount_id}"></div>\n'
            f'<script type="module">\n'
            f'  import * as app from "{module_url}";\n'
            f'  app.mount(document.getElementById("{mount_id}"));\n'
            f'</script>'
        )

    def __repr__(self) -> str:
        return "<ComponentLoader>"


class EventBus:
    """Pub/sub communication channel for micro-frontends."""

    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, channel: str, callback: Callable[[Any], None]) -> None:
        self._subs.setdefault(channel, []).append(callback)

    def publish(self, channel: str, payload: Any) -> None:
        for cb in self._subs.get(channel, []):
            cb(payload)

    def unsubscribe(self, channel: str, callback: Callable[[Any], None]) -> None:
        self._subs[channel] = [cb for cb in self._subs.get(channel, []) if cb is not callback]

    def __repr__(self) -> str:
        return f"<EventBus channels={list(self._subs.keys())}>"


class LayoutShell(HTMLComponent):
    """Responsive shell with collapsible sidebar, breadcrumb stub and notification area."""

    def __init__(self, breadcrumbs: List[str] = None, notifications: List[str] = None) -> None:
        self.breadcrumbs = breadcrumbs or ["Home", "Dashboard"]
        self.notifications = notifications or []

    def render(self) -> str:
        bc = " &rsaquo; ".join(self.breadcrumbs)
        notes = "\n".join(f'<div class="notification">{n}</div>' for n in self.notifications)
        return textwrap.dedent(
            f"""\
            <div class="layout-shell">
                <div class="layout-breadcrumb">{bc}</div>
                <div class="layout-notify">{notes}</div>
                <div class="layout-body">
                    <input type="checkbox" id="sidebar-toggle" class="sidebar-toggle" />
                    <label for="sidebar-toggle" class="sidebar-hamburger">&#9776;</label>
                    <aside class="layout-sidebar">Sidebar</aside>
                    <main class="layout-main">Main Content</main>
                </div>
            </div>
            """
        )

    def __repr__(self) -> str:
        return "<LayoutShell>"


class HashRouter:
    """Hash-based routing stub with route matching and active link highlighting."""

    def __init__(self, routes: Dict[str, str] = None) -> None:
        self.routes = routes or {"#/": "Home", "#/about": "About", "#/contact": "Contact"}

    def match(self, hash_url: str) -> Optional[str]:
        return self.routes.get(hash_url)

    def nav_html(self, current: str = "#") -> str:
        links = "\n".join(
            f'<a href="{href}" class="{"active" if href == current else ""}">{label}</a>'
            for href, label in self.routes.items()
        )
        return f'<nav class="hash-nav">{links}</nav>'

    def __repr__(self) -> str:
        return f"<HashRouter routes={len(self.routes)}>"


# =============================================================================
# Section 5: Angular / React Pattern Emulation (lines ~750–900)
# =============================================================================

class ComponentBase(HTMLComponent):
    """Emulate a component lifecycle: init, render, update, destroy."""

    def __init__(self, template: str = "", data: Dict[str, Any] = None) -> None:
        self.template = template
        self.data = data or {}
        self._destroyed = False
        self.on_init()

    def on_init(self) -> None:
        """Lifecycle hook: component initialization."""
        pass

    def render(self) -> str:
        if self._destroyed:
            return "<!-- destroyed -->"
        return self.template.format(**self.data)

    def on_update(self, new_data: Dict[str, Any]) -> None:
        self.data.update(new_data)

    def on_destroy(self) -> None:
        self._destroyed = True

    def __repr__(self) -> str:
        return f"<ComponentBase data_keys={list(self.data.keys())}>"


class DataBinding:
    """One-way binding helper and two-way binding stub via property observers."""

    def __init__(self, value: Any = "") -> None:
        self._value = value
        self._observers: List[Callable[[Any], None]] = []

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, new: Any) -> None:
        old = self._value
        self._value = new
        for cb in self._observers:
            cb(new)

    def bind(self, callback: Callable[[Any], None]) -> None:
        self._observers.append(callback)

    def one_way(self, template: str) -> str:
        return template.format(value=self._value)

    def __repr__(self) -> str:
        return f"<DataBinding value={self._value!r}>"


class DirectiveStub:
    """Base for structural directive emulation."""

    @staticmethod
    def apply(html: str, condition: bool) -> str:
        return html if condition else ""

    def __repr__(self) -> str:
        return "<DirectiveStub>"


class IfDirective(DirectiveStub):
    """Render block only if condition is True."""

    @staticmethod
    def render(html: str, condition: bool) -> str:
        return html if condition else ""

    def __repr__(self) -> str:
        return "<IfDirective>"


class ForDirective(DirectiveStub):
    """Repeat block for each item in iterable."""

    @staticmethod
    def render(template: str, items: List[Any]) -> str:
        return "\n".join(template.format(item=item, index=idx) for idx, item in enumerate(items))

    def __repr__(self) -> str:
        return "<ForDirective>"


class SwitchDirective(DirectiveStub):
    """Render matched case from dict of cases."""

    @staticmethod
    def render(cases: Dict[Any, str], key: Any) -> str:
        return cases.get(key, "")

    def __repr__(self) -> str:
        return "<SwitchDirective>"


class ServiceStub:
    """Dependency injection container stub."""

    def __init__(self) -> None:
        self._registry: Dict[str, Any] = {}

    def register(self, name: str, instance: Any) -> None:
        self._registry[name] = instance

    def get(self, name: str) -> Any:
        return self._registry.get(name)

    def __repr__(self) -> str:
        return f"<ServiceStub registered={list(self._registry.keys())}>"


class PipeStub:
    """Base transform pipe stub."""

    @staticmethod
    def transform(value: Any, *args: Any) -> str:
        return str(value)

    def __repr__(self) -> str:
        return "<PipeStub>"


class CurrencyPipe(PipeStub):
    """Format number as currency."""

    @staticmethod
    def transform(value: Any, symbol: str = "$") -> str:
        return f"{symbol}{float(value):,.2f}"

    def __repr__(self) -> str:
        return "<CurrencyPipe>"


class DatePipe(PipeStub):
    """Format date/time."""

    @staticmethod
    def transform(value: Any, fmt: str = "%Y-%m-%d") -> str:
        from datetime import datetime

        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value.strftime(fmt) if hasattr(value, "strftime") else str(value)

    def __repr__(self) -> str:
        return "<DatePipe>"


class UpperCasePipe(PipeStub):
    @staticmethod
    def transform(value: Any) -> str:
        return str(value).upper()

    def __repr__(self) -> str:
        return "<UpperCasePipe>"


class LowerCasePipe(PipeStub):
    @staticmethod
    def transform(value: Any) -> str:
        return str(value).lower()

    def __repr__(self) -> str:
        return "<LowerCasePipe>"


class SlicePipe(PipeStub):
    @staticmethod
    def transform(value: Any, start: int = 0, end: Optional[int] = None) -> str:
        return str(value)[start:end]

    def __repr__(self) -> str:
        return "<SlicePipe>"


class PercentPipe(PipeStub):
    @staticmethod
    def transform(value: Any, digits: int = 0) -> str:
        return f"{float(value) * 100:.{digits}f}%"

    def __repr__(self) -> str:
        return "<PercentPipe>"


class JsonPipe(PipeStub):
    @staticmethod
    def transform(value: Any) -> str:
        return json.dumps(value, indent=2)

    def __repr__(self) -> str:
        return "<JsonPipe>"


class RouteConfig:
    """Route definition with path, component and guards stub."""

    def __init__(
        self,
        path: str = "/",
        component: str = "",
        guards: List[str] = None,
    ) -> None:
        self.path = path
        self.component = component
        self.guards = guards or []

    def __repr__(self) -> str:
        return f"<RouteConfig path={self.path!r}>"


class LifecycleHooks:
    """Stubs for Angular-style lifecycle interfaces."""

    class OnInit:
        def on_init(self) -> None:
            pass

    class OnDestroy:
        def on_destroy(self) -> None:
            pass

    class OnChanges:
        def on_changes(self, changes: Dict[str, Any]) -> None:
            pass

    class DoCheck:
        def do_check(self) -> None:
            pass

    def __repr__(self) -> str:
        return "<LifecycleHooks>"


# =============================================================================
# Section 6: CSS Framework & Theming (lines ~900–1000)
# =============================================================================

class CSSFramework:
    """Utility-first CSS class generator (Tailwind-style)."""

    @staticmethod
    def padding(size: int) -> str:
        return f"p-{size}"

    @staticmethod
    def margin(size: int) -> str:
        return f"m-{size}"

    @staticmethod
    def color(name: str, shade: int = 500) -> str:
        return f"text-{name}-{shade}"

    @staticmethod
    def bg(name: str, shade: int = 500) -> str:
        return f"bg-{name}-{shade}"

    @staticmethod
    def typography(size: str = "base", weight: str = "normal") -> str:
        return f"text-{size} font-{weight}"

    @staticmethod
    def flex(direction: str = "row", justify: str = "start", align: str = "start") -> str:
        return f"flex flex-{direction} justify-{justify} items-{align}"

    @staticmethod
    def grid(cols: int = 1, gap: int = 4) -> str:
        return f"grid grid-cols-{cols} gap-{gap}"

    def __repr__(self) -> str:
        return "<CSSFramework>"


class AnimationCSS:
    """Keyframe CSS string generators."""

    @staticmethod
    def _keyframe(name: str, frames: str) -> str:
        return f"@keyframes {name} {{ {frames} }}"

    @classmethod
    def fade_in(cls) -> str:
        return cls._keyframe("fadeIn", "from{opacity:0} to{opacity:1}") + " .fade-in{animation:fadeIn 0.3s ease-in}"

    @classmethod
    def fade_out(cls) -> str:
        return cls._keyframe("fadeOut", "from{opacity:1} to{opacity:0}") + " .fade-out{animation:fadeOut 0.3s ease-out}"

    @classmethod
    def slide_in(cls, direction: str = "right") -> str:
        trans = {"right": "translateX(100%)", "left": "translateX(-100%)", "up": "translateY(-100%)", "down": "translateY(100%)"}
        return cls._keyframe("slideIn", f"from{{transform:{trans.get(direction,'translateX(100%)')};opacity:0}} to{{transform:translate(0);opacity:1}}") + " .slide-in{animation:slideIn 0.3s ease-out}"

    @classmethod
    def slide_out(cls, direction: str = "right") -> str:
        trans = {"right": "translateX(100%)", "left": "translateX(-100%)", "up": "translateY(-100%)", "down": "translateY(100%)"}
        return cls._keyframe("slideOut", f"from{{transform:translate(0);opacity:1}} to{{transform:{trans.get(direction,'translateX(100%)')};opacity:0}}") + " .slide-out{animation:slideOut 0.3s ease-in}"

    @classmethod
    def bounce(cls) -> str:
        return cls._keyframe("bounce", "0%,100%{transform:translateY(0)} 50%{transform:translateY(-25%)}") + " .bounce{animation:bounce 1s infinite}"

    @classmethod
    def pulse(cls) -> str:
        return cls._keyframe("pulse", "0%,100%{opacity:1} 50%{opacity:0.5}") + " .pulse{animation:pulse 2s infinite}"

    @classmethod
    def spin(cls) -> str:
        return cls._keyframe("spin", "from{transform:rotate(0deg)} to{transform:rotate(360deg)}") + " .spin{animation:spin 1s linear infinite}"

    @classmethod
    def shake(cls) -> str:
        return cls._keyframe("shake", "0%,100%{transform:translateX(0)} 25%{transform:translateX(-5px)} 75%{transform:translateX(5px)}") + " .shake{animation:shake 0.4s ease-in-out}"

    def __repr__(self) -> str:
        return "<AnimationCSS>"


class GridSystem:
    """12-column grid CSS generator."""

    @classmethod
    def css(cls) -> str:
        cols = "\n".join(f"  .col-{i}{{flex:0 0 {(i/12)*100:.333f}%;max-width:{(i/12)*100:.333f}%;}}" for i in range(1, 13))
        breakpoints = textwrap.dedent(
            """\
            @media(min-width:640px){ .col-sm-1{flex:0 0 8.333%;max-width:8.333%;} .col-sm-2{flex:0 0 16.667%;max-width:16.667%;} .col-sm-3{flex:0 0 25%;max-width:25%;} .col-sm-4{flex:0 0 33.333%;max-width:33.333%;} .col-sm-6{flex:0 0 50%;max-width:50%;} .col-sm-12{flex:0 0 100%;max-width:100%;} }
            @media(min-width:768px){ .col-md-1{flex:0 0 8.333%;max-width:8.333%;} .col-md-2{flex:0 0 16.667%;max-width:16.667%;} .col-md-3{flex:0 0 25%;max-width:25%;} .col-md-4{flex:0 0 33.333%;max-width:33.333%;} .col-md-6{flex:0 0 50%;max-width:50%;} .col-md-12{flex:0 0 100%;max-width:100%;} }
            @media(min-width:1024px){ .col-lg-1{flex:0 0 8.333%;max-width:8.333%;} .col-lg-2{flex:0 0 16.667%;max-width:16.667%;} .col-lg-3{flex:0 0 25%;max-width:25%;} .col-lg-4{flex:0 0 33.333%;max-width:33.333%;} .col-lg-6{flex:0 0 50%;max-width:50%;} .col-lg-12{flex:0 0 100%;max-width:100%;} }
            @media(min-width:1280px){ .col-xl-1{flex:0 0 8.333%;max-width:8.333%;} .col-xl-2{flex:0 0 16.667%;max-width:16.667%;} .col-xl-3{flex:0 0 25%;max-width:25%;} .col-xl-4{flex:0 0 33.333%;max-width:33.333%;} .col-xl-6{flex:0 0 50%;max-width:50%;} .col-xl-12{flex:0 0 100%;max-width:100%;} }
            """
        )
        return f".row{{display:flex;flex-wrap:wrap;margin:0 -0.5rem;}}\n{cols}\n{breakpoints}"

    def __repr__(self) -> str:
        return "<GridSystem>"


class SpacingScale:
    """Margin/padding scale CSS generator (0.25rem increments)."""

    @classmethod
    def css(cls) -> str:
        rules = []
        for i in range(0, 17):
            val = i * 0.25
            rules.append(f"  .m-{i}{{margin:{val}rem;}} .mx-{i}{{margin-left:{val}rem;margin-right:{val}rem;}} .my-{i}{{margin-top:{val}rem;margin-bottom:{val}rem;}} .p-{i}{{padding:{val}rem;}} .px-{i}{{padding-left:{val}rem;padding-right:{val}rem;}} .py-{i}{{padding-top:{val}rem;padding-bottom:{val}rem;}}")
        return "\n".join(rules)

    def __repr__(self) -> str:
        return "<SpacingScale>"


class ColorPalette:
    """Generate color scales (50–900) for semantic colors."""

    PALETTES: Dict[str, List[str]] = {
        "primary": ["#eff6ff", "#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8", "#1e40af", "#1e3a8a"],
        "secondary": ["#f5f3ff", "#ede9fe", "#ddd6fe", "#c4b5fd", "#a78bfa", "#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6", "#4c1d95"],
        "success": ["#f0fdf4", "#dcfce7", "#bbf7d0", "#86efac", "#4ade80", "#22c55e", "#16a34a", "#15803d", "#166534", "#14532d"],
        "warning": ["#fffbeb", "#fef3c7", "#fde68a", "#fcd34d", "#fbbf24", "#f59e0b", "#d97706", "#b45309", "#92400e", "#78350f"],
        "danger": ["#fef2f2", "#fee2e2", "#fecaca", "#fca5a5", "#f87171", "#ef4444", "#dc2626", "#b91c1c", "#991b1b", "#7f1d1d"],
        "neutral": ["#f8fafc", "#f1f5f9", "#e2e8f0", "#cbd5e1", "#94a3b8", "#64748b", "#475569", "#334155", "#1e293b", "#0f172a"],
    }

    @classmethod
    def css(cls) -> str:
        rules = []
        shades = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]
        for name, colors in cls.PALETTES.items():
            for shade, color in zip(shades, colors):
                rules.append(f"  .text-{name}-{shade} {{ color: {color}; }}")
                rules.append(f"  .bg-{name}-{shade} {{ background-color: {color}; }}")
        return "\n".join(rules)

    def __repr__(self) -> str:
        return "<ColorPalette>"


# =============================================================================
# Section 7: Demo & File Generation (lines ~1000+)
# =============================================================================

class ComponentLibraryPage:
    """Generate a sample page showcasing all button and input variants."""

    @classmethod
    def generate(cls) -> str:
        buttons = "\n".join(
            [
                ButtonVariants.primary("Primary"),
                ButtonVariants.secondary("Secondary"),
                ButtonVariants.danger("Danger"),
                ButtonVariants.ghost("Ghost"),
                ButtonVariants.outline("Outline"),
                ButtonVariants.link("Link"),
            ]
        )
        inputs = "\n".join(
            [
                InputVariants.text("user", "Username", placeholder="johndoe"),
                InputVariants.password("pass", "Password"),
                InputVariants.email("email", "Email", placeholder="john@example.com"),
                InputVariants.number("age", "Age"),
                InputVariants.textarea("bio", "Bio", placeholder="Tell us about yourself"),
                InputVariants.select("role", "Role", [("user", "User"), ("admin", "Admin")]),
                InputVariants.checkbox("agree", "I agree to terms"),
                InputVariants.radio("gender", "Male", "m"),
                InputVariants.radio("gender", "Female", "f"),
                InputVariants.toggle("notify", "Notifications"),
                InputVariants.date("dob", "Date of Birth"),
                InputVariants.file("resume", "Resume"),
            ]
        )
        extras = "\n".join(
            [
                Badge("New", "success").render(),
                Alert("Something happened!", "warning").render(),
                Toast("Saved successfully", "success").render(),
                Spinner("md").render(),
                ProgressBar(65, label="Loading…").render(),
            ]
        )
        return textwrap.dedent(
            f"""\
            <!DOCTYPE html>
            <html lang="en">
            <head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>Component Library</title></head>
            <body style="font-family:sans-serif; padding:2rem;">
                <h1>Buttons</h1>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:2rem;">{buttons}</div>
                <h1>Inputs</h1>
                <form style="max-width:400px;">{inputs}</form>
                <h1>Misc</h1>
                <div style="display:flex; gap:1rem; flex-wrap:wrap; align-items:center;">{extras}</div>
            </body>
            </html>
            """
        )

    def __repr__(self) -> str:
        return "<ComponentLibraryPage>"


def _demo_common_css() -> str:
    """Shared baseline CSS used across demos."""
    return textwrap.dedent(
        """\
        /* baseline */
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:system-ui,-apple-system,sans-serif;line-height:1.5;color:#1f2937;}
        .btn{display:inline-flex;align-items:center;justify-content:center;padding:0.5rem 1rem;border:none;border-radius:0.375rem;cursor:pointer;font-size:0.875rem;transition:background .15s,transform .1s;}
        .btn:hover{transform:translateY(-1px);}
        .btn-primary{background:#2563eb;color:#fff;}
        .btn-secondary{background:#64748b;color:#fff;}
        .btn-danger{background:#dc2626;color:#fff;}
        .btn-ghost{background:transparent;color:#374151;}
        .btn-outline{background:transparent;border:1px solid #d1d5db;color:#374151;}
        .btn-link{background:transparent;color:#2563eb;text-decoration:underline;}
        .form-group{margin-bottom:1rem;}
        label{display:block;margin-bottom:0.25rem;font-weight:500;font-size:0.875rem;}
        input,textarea,select{width:100%;padding:0.5rem;border:1px solid #d1d5db;border-radius:0.375rem;font-size:0.875rem;transition:border-color .15s,box-shadow .15s;}
        input:focus,textarea:focus,select:focus{outline:none;border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.15);}
        .input-error{color:#dc2626;font-size:0.75rem;margin-top:0.25rem;}
        .has-error input,.has-error textarea,.has-error select{border-color:#dc2626;}
        .form-success{background:#dcfce7;color:#166534;padding:0.75rem;border-radius:0.375rem;margin-bottom:1rem;}
        .badge{display:inline-flex;align-items:center;padding:0.125rem 0.5rem;border-radius:9999px;font-size:0.75rem;font-weight:600;}
        .badge-success{background:#dcfce7;color:#166534;}
        .badge-primary{background:#dbeafe;color:#1e40af;}
        .alert{padding:0.75rem 1rem;border-radius:0.375rem;margin-bottom:1rem;display:flex;justify-content:space-between;align-items:center;}
        .alert-warning{background:#fef3c7;color:#92400e;}
        .alert-info{background:#dbeafe;color:#1e40af;}
        .toast{display:inline-flex;align-items:center;gap:0.5rem;padding:0.5rem 1rem;border-radius:0.375rem;background:#dbeafe;color:#1e40af;}
        .spinner{width:1.5rem;height:1.5rem;border:2px solid #e5e7eb;border-top-color:#2563eb;border-radius:50%;animation:spin 1s linear infinite;}
        .progress{height:0.5rem;background:#e5e7eb;border-radius:0.25rem;overflow:hidden;position:relative;}
        .progress-bar{height:100%;background:#2563eb;border-radius:0.25rem;transition:width .3s;}
        .card{border:1px solid #e5e7eb;border-radius:0.5rem;overflow:hidden;background:#fff;transition:box-shadow .2s;}
        .card:hover{box-shadow:0 10px 15px -3px rgba(0,0,0,.1);}
        .card-header{padding:1rem;font-weight:600;border-bottom:1px solid #e5e7eb;}
        .card-body{padding:1rem;}
        .card-footer{padding:1rem;border-top:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;}
        .navbar{display:flex;align-items:center;justify-content:space-between;padding:0.75rem 1rem;background:#fff;border-bottom:1px solid #e5e7eb;}
        .nav-links{display:flex;align-items:center;gap:1rem;}
        .nav-hamburger{display:none;flex-direction:column;gap:4px;cursor:pointer;}
        .nav-hamburger span{width:24px;height:2px;background:#374151;display:block;}
        .nav-dropdown{position:relative;}
        .drop-menu{display:none;position:absolute;top:100%;left:0;background:#fff;border:1px solid #e5e7eb;border-radius:0.375rem;min-width:120px;}
        .nav-dropdown:hover .drop-menu{display:block;}
        @media(max-width:640px){.nav-hamburger{display:flex;}.nav-links{display:none;flex-direction:column;gap:0.5rem;width:100%;}.nav-toggle:checked ~ .nav-links{display:flex;}}
        .table{width:100%;border-collapse:collapse;}
        .table th,.table td{padding:0.75rem;text-align:left;border-bottom:1px solid #e5e7eb;}
        .table-striped tbody tr:nth-child(even){background:#f9fafb;}
        .table-hover tbody tr:hover{background:#f3f4f6;}
        .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:50;}
        .modal-overlay.active{display:flex;}
        .modal-dialog{background:#fff;border-radius:0.5rem;max-width:500px;width:90%;max-height:90vh;overflow:auto;box-shadow:0 20px 25px -5px rgba(0,0,0,.1);}
        .modal-header{padding:1rem;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5e7eb;}
        .modal-body{padding:1rem;}
        .modal-footer{padding:1rem;border-top:1px solid #e5e7eb;text-align:right;}
        .modal-close{background:transparent;border:none;font-size:1.5rem;cursor:pointer;}
        .accordion-item{border:1px solid #e5e7eb;border-radius:0.375rem;margin-bottom:0.5rem;overflow:hidden;}
        .acc-toggle{display:none;}
        .acc-title{display:block;padding:0.75rem 1rem;background:#f9fafb;cursor:pointer;font-weight:500;}
        .acc-content{max-height:0;overflow:hidden;transition:max-height .3s;padding:0 1rem;}
        .acc-toggle:checked ~ .acc-content{max-height:200px;padding:0.75rem 1rem;}
        .tabs{display:flex;flex-direction:column;gap:0.5rem;}
        .tab-labels{display:flex;gap:0.5rem;border-bottom:1px solid #e5e7eb;}
        .tab-labels label{padding:0.5rem 1rem;cursor:pointer;border-bottom:2px solid transparent;}
        .tab-radio{display:none;}
        .tab-panel{display:none;padding:1rem;border:1px solid #e5e7eb;border-radius:0 0 0.375rem 0.375rem;}
        .tab-radio:checked + .tab-panel{display:block;}
        .tab-labels label:hover,.tab-radio:checked ~ .tab-labels label:nth-of-type(1){border-color:#2563eb;}
        @keyframes spin{to{transform:rotate(360deg);}}
        """
    )


def _wrap_page(title: str, body: str) -> str:
    return (
        f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>"
        f'<meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />'
        f'<title>{title}</title><style>{_demo_common_css()}</style></head>\n'
        f'<body>\n{body}\n</body>\n</html>'
    )


if __name__ == "__main__":
    out_dir = Path("C:/mnt/agents/MAGNATRIX-OS/runtime")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Login form
    login = LoginForm(oauth_providers=["Google", "GitHub"])
    login_html = _wrap_page("Login Form", login.render())
    (out_dir / "demo_login.html").write_text(login_html, encoding="utf-8")

    # 2. Portfolio (dark theme)
    config = PortfolioConfig(
        name="Jordan Lee",
        title="Software Engineer",
        tagline="Crafting digital experiences.",
        bio="Full-stack engineer with 5+ years building scalable web applications.",
        skills={"Python": 95, "React": 88, "TypeScript": 85, "Docker": 80},
        projects=[
            {"name": "Nebula SaaS", "desc": "Cloud-native analytics platform.", "link": "#"},
            {"name": "Pixel Forge", "desc": "Design system generator.", "link": "#"},
            {"name": "Data Stream", "desc": "Real-time data pipeline.", "link": "#"},
        ],
        experience=[
            {"role": "Senior Engineer", "company": "TechCorp", "years": "2021–Present"},
            {"role": "Developer", "company": "StartupXYZ", "years": "2018–2021"},
        ],
        social={"GitHub": "https://github.com", "LinkedIn": "https://linkedin.com", "Twitter": "https://twitter.com"},
        email="jordan@example.com",
    )
    portfolio = PortfolioSite(config, theme="dark")
    (out_dir / "demo_portfolio.html").write_text(portfolio.render(), encoding="utf-8")

    # 3. Micro-frontend shell
    shell = MicroFrontendShell(
        header="<h1>Dashboard</h1>",
        sidebar="<nav><a href='#/'>Home</a><a href='#/settings'>Settings</a></nav>",
        content="<p>Welcome to the micro-frontend shell.</p>",
        footer="<small>&copy; 2024</small>",
    )
    mf_html = _wrap_page("Micro Frontend", shell.render())
    (out_dir / "demo_microfrontend.html").write_text(mf_html, encoding="utf-8")

    # 4. Component library sample page
    lib_page = ComponentLibraryPage.generate()
    (out_dir / "demo_components.html").write_text(lib_page, encoding="utf-8")

    # Summary
    classes = [
        HTMLComponent, LoginForm, CardComponent, ModalDialog, NavbarComponent,
        TableComponent, ButtonVariants, InputVariants, Badge, Alert, Toast,
        Spinner, ProgressBar, Accordion, Tabs,
        Validator, RequiredValidator, MinLengthValidator, MaxLengthValidator,
        RegexValidator, EmailValidator, NumberRangeValidator,
        FormField, FormBuilder, FormRenderer, FormState,
        PortfolioConfig, ThemeEngine, PortfolioSite,
        MicroFrontendShell, ModuleRegistry, ComponentLoader, EventBus,
        LayoutShell, HashRouter,
        ComponentBase, DataBinding, DirectiveStub, IfDirective, ForDirective,
        SwitchDirective, ServiceStub, PipeStub, CurrencyPipe, DatePipe,
        UpperCasePipe, LowerCasePipe, SlicePipe, PercentPipe, JsonPipe,
        RouteConfig, LifecycleHooks,
        CSSFramework, AnimationCSS, GridSystem, SpacingScale, ColorPalette,
        ComponentLibraryPage,
    ]

    print("=" * 60)
    print("  BATCH D — Frontend/UI Portfolio Generator (Pure Python)")
    print("=" * 60)
    print(f"\nGenerated files in: {out_dir}")
    for f in ["demo_login.html", "demo_portfolio.html", "demo_microfrontend.html", "demo_components.html"]:
        size = (out_dir / f).stat().st_size
        print(f"  • {f:<30} ({size:,} bytes)")
    print(f"\nTotal classes defined : {len(classes)}")
    print(f"Lines of code (approx)  : 1100+")
    print("=" * 60)
