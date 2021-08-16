class ShakeMissingException(Exception):
    """Thrown when a synchronization point is missing, e.g., a second shake could not be found in the signal."""

    pass


class BadThresholdException(Exception):
    """Thrown if the shake threshold is below 0 or above 1."""

    pass


class StartEqualsEndError(Exception):
    """
    Thrown when the detected start synchronization point equals the end synchronization point.
    Maybe change the detection window lengths?
    """

    pass


class BadWindowException(Exception):
    """Thrown when the sync point detection window length is longer than the data"""

    pass
