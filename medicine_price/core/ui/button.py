from dataclasses import dataclass, field
from typing import Dict, Optional

from django.urls import reverse


@dataclass
class HTMXButton:
    name: str
    label: str
    icon: str
    url_name: str
    url_kwargs: Dict[str, object] = field(default_factory=dict)

    css_class: str = "btn btn-outline-info"
    hx_method: str = "get"
    hx_target: str = "#main-content"
    hx_push_url: str = "true"
    hx_swap: str = "innerHTML"

    confirm: Optional[str] = None # текст підтвердження
    disabled: bool = False

    def url(self) -> str:
        return reverse(self.url_name, kwargs=self.url_kwargs) if self.url_name else "#"

    def htmx_attrs(self) -> Dict[str, str]:
        attrs = {
            f"hx-{self.hx_method}": self.url(),
            "hx-target": self.hx_target,
            "hx-push-url": self.hx_push_url,
            "hx-swap": self.hx_swap,
        }
        if self.confirm:
            attrs["hx-confirm"] = self.confirm
        return attrs



class UIButtons:
    DEFAULT_CSS_CLASS = 'btn btn-outline-info me-2'

    def __init__(self):
        self.name = 'Button'
        self.url_name = '#'
        self.kwargs  = {}
        self.icon = None
        self.css_class = self.DEFAULT_CSS_CLASS


    def build(self, name, label, icon, url_name, hx_target, kwargs=None) -> HTMXButton:
        return HTMXButton(
            name=name,
            label=label,
            icon=icon or 'bi bi-heart-pulse me-2',
            url_name=url_name,
            url_kwargs=kwargs or self.kwargs,
            css_class=self.css_class,
            hx_target=hx_target,
        )