
def get_parameter(
    name: str,
    default: str = "",
    required: bool = True,
) -> str:
    """
    Retrieves a Databricks notebook parameter.

    Args:
        name: Parameter name.
        default: Default value shown in the widget.
        required: Whether the parameter is mandatory.

    Returns:
        Parameter value.

    Raises:
        ValueError: If a required parameter is empty.
        RuntimeError: If executed outside a Databricks notebook.
    """
    try:
        dbutils.widgets.text(name, default, name.title())
        value = dbutils.widgets.get(name).strip()
    except NameError as exc:
        raise RuntimeError(
            "This function must be executed inside a Databricks notebook."
        ) from exc

    if required and not value:
        raise ValueError(f"Parameter '{name}' is required.")

    return value
