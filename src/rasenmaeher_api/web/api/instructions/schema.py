"""Instruction response schemas"""

from typing import Dict, Optional, Any

from pydantic import BaseModel, Extra, Field
from libpvarki.schemas.product import UserInstructionFragment
from pydantic_collections import BaseCollectionModel

# pylint: disable=too-few-public-methods


class AllProductsInstructionFragments(BaseModel):
    """DEPRECATED! Fragments for all products"""

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


class ProductFile(BaseModel):  # pylint: disable=too-few-public-methods
    """File description"""

    title: str = Field(description="Title for the file")
    filename: str = Field(description="file name")
    data: str = Field(description="data-url for the file")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid


class ProductFileList(BaseCollectionModel[ProductFile]):  # type: ignore[misc]
    """List of files"""

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic configs"""

        extra = Extra.forbid


class AllProductsInstructionFiles(BaseModel):
    """DEPRECATED! user files for all products"""

    files: Dict[str, Optional[ProductFileList]] = Field(
        description="files keyed by product short name, if fetching failed value for that product is null"
    )

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid


# FIXME: Move to libpvarki
class InstructionData(BaseModel):
    """Instruction data response"""

    callsign: str = Field(description="Which callsign this was created for (can be used for sanity-checking)")
    language: str = Field(description="Language that was resolved, might not be same as requested")
    instructions: Any = Field(description="The actual instruction data, in whatever format the React UI wants it")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid


class ProductData(BaseModel):
    """Product user data for modular UI"""

    data: Dict[str, Any] = Field(description="User data required for modular UI.")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
