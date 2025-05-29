# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/4/2 16:06
# @Author  : wangchongshi
# @Email   : wangchongshi.wcs@antgroup.com
# @FileName: llm_output.py
from typing import Any, Optional

from pydantic import BaseModel

from agentuniverse.agent.memory.message import Message


class LLMOutput(BaseModel):
    """The basic class for llm output."""

    """The text of the llm output."""
    text: str

    """The raw data of the llm output."""
    raw: Optional[Any] = None

    message: Optional[Message] = None
