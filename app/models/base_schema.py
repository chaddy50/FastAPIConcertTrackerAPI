from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Base for input schemas (Create, Update). Fields are snake_case, matching the API's native convention."""
    model_config = ConfigDict()


class ReadSchema(BaseModel):
    """Base for response schemas (Read). Built from ORM objects, serialized as snake_case."""
    model_config = ConfigDict(
        from_attributes=True,
    )
