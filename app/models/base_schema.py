from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    """Base for input schemas (Create, Update). Accepts both camelCase and snake_case input."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ReadSchema(BaseModel):
    """Base for response schemas (Read). Builds from ORM objects and serializes to camelCase."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )
