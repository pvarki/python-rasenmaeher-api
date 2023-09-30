"""Instruction response schemas"""
from typing import Dict, Optional

from pydantic import BaseModel, Extra, Field
from libpvarki.schemas.product import UserInstructionFragment


class AllProdcutsInstructionFragments(BaseModel):  # pylint: disable=too-few-public-methods
    """Fragments for all products"""

    fragments: Dict[str, Optional[UserInstructionFragment]] = Field(
        description="Instructions keyed by product short name, if fetching of fragment failed value for that product is null"  # pylint: disable=C0301
    )

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "fragments": {
                        "tak": {
                            "html": """<p class="hello">Hello World!</p>""",
                            "inject_css": "http://example.com/mystyle.css",
                        },
                        "nosuchproduct": None,
                    }
                },
            ],
        }
