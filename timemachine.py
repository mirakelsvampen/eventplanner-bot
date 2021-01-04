import re

from datetime import datetime

class TimeMachine( object ):
    """
        Create a report on a string represending a point in time.
        Arguments must be formated in such a way that the following timedate filters applicable:
        
        %y - Large year
        %Y - Small year
        %m - Month
        %d - Day
        %H - Hour
        %M - Minute
        
        Special characters such as whitespace, colons etc are allowed
    """
    def __init__(self, datain):
        """
            turn the string into an array of integers
        """
        self.time_string = re.sub(r'\W+', '', datain)

        try:
            self.time = datetime.strptime(self.time_string, '%y%m%d%H%M')
        except ValueError:
            self.time = datetime.strptime(self.time_string, '%Y%m%d%H%M')
        else:
            raise ValueError('Invalid format must be: "%y%m%d%H%M" or "%Y%m%d%H%M"')

    def convert(self):
        """
            Return a valid datetime object to the caller
        """
        return self.time

    def is_in_past(self):
        """
            See if a point in time is the past
        """
        pass

if __name__ == '__main__':
    time = TimeMachine('201708222359')
    if time.to_datetime():
        print('The time is valid!')
    else:
        print('The time is not valid :(')
