import logging

import sqlglot
import sqlglot.errors

logger = logging.getLogger(__name__)

# Only these statement types are allowed
ALLOWED_STATEMENTS = {"Select"}


class UnsafeSQLError(Exception):
    """Raised when the generated SQL contains unsafe operations."""
    pass


def validate(sql: str) -> None:
    """
    Validates that a SQL query is safe to execute.

    Why sqlglot instead of a simple blacklist?
    A blacklist like checking for 'DROP' or 'DELETE' can be bypassed with
    mixed casing (e.g. 'DrOp') or comments (e.g. 'DR--\nOP').
    sqlglot parses the SQL properly and checks the actual statement type,
    making it much harder to bypass.

    Raises UnsafeSQLError if the query is not a SELECT or WITH statement.
    """
    try:
        statements = sqlglot.parse(sql)
    except sqlglot.errors.ParseError as e:
        logger.warning(f"SQL parse error: {e}")
        raise UnsafeSQLError(f"Could not parse SQL: {e}")

    if not statements:
        raise UnsafeSQLError("No SQL statement found.")

    for statement in statements:
        statement_type = type(statement).__name__

        if statement_type not in ALLOWED_STATEMENTS:
            logger.warning(f"Unsafe SQL blocked — statement type: {statement_type}")
            raise UnsafeSQLError(
                f"Unsafe operation detected: '{statement_type}'. "
                f"Only SELECT queries are allowed."
            )

    logger.info("SQL validation passed.")