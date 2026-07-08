import logging
from typing import Union
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class BaseConfig(BaseModel):
    IS_PROD: Union[bool]
    SHOW_MODE: Union[bool]
    MODELS_HALF: Union[bool]
    MODELS_ENABLE_TRACKING: Union[bool]

    ROOT_DIR: Union[str]
    STATIC_DIR: Union[str]



class ConfigsValidator(BaseConfig):
    pass