"""通用服务层能力：基础校验与 CRUD 助手。"""

from app.services.common.crud import (
    create_and_refresh,
    delete_if_exists,
    flush_and_refresh,
    get_or_404,
    patch_model,
)
from app.services.common.errors import (
    entity_already_exists,
    entity_not_found,
    invalid_choice,
    not_belong_to,
    relation_mismatch,
    required_field,
)
from app.services.common.validators import (
    ensure_not_exists,
    require_entity,
    require_optional_entity,
)

__all__ = [
    "create_and_refresh",
    "delete_if_exists",
    "entity_already_exists",
    "entity_not_found",
    "ensure_not_exists",
    "flush_and_refresh",
    "get_or_404",
    "invalid_choice",
    "not_belong_to",
    "patch_model",
    "relation_mismatch",
    "required_field",
    "require_entity",
    "require_optional_entity",
]
