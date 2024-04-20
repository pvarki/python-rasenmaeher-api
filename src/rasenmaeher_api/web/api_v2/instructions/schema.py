"""Instruction response schemas"""
from typing import Dict, Optional

from pydantic import BaseModel, Extra, Field
from libpvarki.schemas.product import UserInstructionFragment
from pydantic_collections import BaseCollectionModel


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


class ProductFile(BaseModel):  # pylint: disable=too-few-public-methods
    """File description"""

    title: str = Field(description="Title for the file")
    filename: str = Field(description="file name")
    data: str = Field(description="data-url for the file")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid


class ProductFileList(BaseCollectionModel[ProductFile]):  # type: ignore[misc]  # pylint: disable=too-few-public-methods
    """List of files"""

    class Config:  # pylint: disable=too-few-public-methods
        """Pydantic configs"""

        extra = Extra.forbid


class AllProdcutsInstructionFiles(BaseModel):  # pylint: disable=too-few-public-methods
    """user files for all products"""

    files: Dict[str, Optional[ProductFileList]] = Field(
        description="files keyed by product short name, if fetching failed value for that product is null"  # pylint: disable=C0301
    )

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
