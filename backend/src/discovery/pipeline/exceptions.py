class CrawlerException(Exception):
    pass

class ConnectorException(CrawlerException):
    pass

class ConnectorNotFoundError(ConnectorException):
    pass

class SelectorChangedError(ConnectorException):
    pass

class UnsupportedBoardError(ConnectorException):
    pass

class NetworkException(CrawlerException):
    pass

class TimeoutError(NetworkException):
    pass

class RateLimitError(NetworkException):
    pass

class DNSFailureError(NetworkException):
    pass

class ParsingException(CrawlerException):
    pass

class DatabaseException(CrawlerException):
    pass

class AuthenticationException(CrawlerException):
    pass
