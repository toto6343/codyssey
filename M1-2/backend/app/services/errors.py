class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class NoDataError(Exception):
    pass


class LLMError(Exception):
    pass


class ConfigError(Exception):
    pass


class RateLimitError(Exception):
    pass
