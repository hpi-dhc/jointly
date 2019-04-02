import abc

class AbstractExtractor(metaclass=abc.ABCMeta):

    def __init__(self):
        self.segments = {}

    @abc.abstractmethod
    def get_segments(self, signals):
        """Detect first and second segments to use for synchronization and
        return dictionary with start and end timestamps for each signal.

        Format of dictionary:
        >>> { 
        >>>     'column_name': {
        >>>         'first': {
        >>>             'start': timestamp,
        >>>             'end': timestamp
        >>>         },
        >>>         'second': {
        >>>             'start': timestamp,
        >>>             'end': timestamp
        >>>         }
        >>>     },
        >>>     ...
        >>> }
        
        """

    def _init_segments(self, columns):
        self.segments = {}
        for column_name in columns:
            self.segments[column_name] = {
                'first': {},
                'second': {},
            }
    
    def _set_first_segment(self, column_name, start, end):
        self.segments[column_name]['first']['start'] = start
        self.segments[column_name]['first']['end'] = end

    def _set_second_segment(self, column_name, start, end):
        self.segments[column_name]['second']['start'] = start
        self.segments[column_name]['second']['end'] = end