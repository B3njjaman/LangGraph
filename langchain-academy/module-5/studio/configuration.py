import os
from dataclasses import dataclass, field, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig
from typing_extensions import Annotated
from dataclasses import dataclass

@dataclass(kw_only=True)
class Configuracion:
    """Los campos configurables del chatbot."""
    id_usuario: str = "usuario-predeterminado"

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuracion":
        """Crea una instancia de Configuracion a partir de un RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        valores: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in valores.items() if v})