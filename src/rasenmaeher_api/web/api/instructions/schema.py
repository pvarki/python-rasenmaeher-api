"""Instruction response schemas"""

from typing import Dict, Optional, Any, List

from pydantic import BaseModel, Field, ConfigDict, RootModel
from libpvarki.schemas.product import UserInstructionFragment


class AllProductsInstructionFragments(BaseModel):
    """DEPRECATED! Fragments for all products"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
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
        },
    )

    fragments: Dict[str, Optional[UserInstructionFragment]] = Field(
        description="Instructions keyed by product short name, if fetching of fragment failed value for that product is null"
    )


class ProductFile(BaseModel):
    """File description"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Title for the file")
    filename: str = Field(description="file name")
    data: str = Field(description="data-url for the file")


class ProductFileList(RootModel[List[ProductFile]]):
    """List of files"""


class AllProductsInstructionFiles(BaseModel):
    """DEPRECATED! user files for all products"""

    model_config = ConfigDict(extra="forbid")

    files: Dict[str, Optional[ProductFileList]] = Field(
        description="files keyed by product short name, if fetching failed value for that product is null"
    )


# FIXME: Move to libpvarki
class InstructionData(BaseModel):
    """Instruction data response"""

    model_config = ConfigDict(extra="forbid")

    callsign: str = Field(description="Which callsign this was created for (can be used for sanity-checking)")
    language: str = Field(description="Language that was resolved, might not be same as requested")
    instructions: Any = Field(description="The actual instruction data, in whatever format the React UI wants it")


class ProductData(BaseModel):
    """Product user data for modular UI"""

    model_config = ConfigDict(extra="forbid")

    data: Dict[str, Any] = Field(description="User data required for modular UI.")
