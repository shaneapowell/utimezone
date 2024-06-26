# --------------------------------------------------------------------- #
# Micropython Timezone Library                                          #
#                                                                       #
# Copyright (C) 2024 by Shane Powell                                    #
# Copyright (C) 2018 by Jack Christensen                                #
# licensed under GNU GPL v3.0, https://www.gnu.org/licenses/gpl.html    #
# --------------------------------------------------------------------- #

import sys
import time
from . import utimezone

_isupy = True if sys.implementation.name == "micropython" else False
_EPOCH_YEAR = time.gmtime(0)[0]


def _mktime(year: int, month: int, day: int, hour: int, min: int, sec: int) -> int:
    """
    Reference: https://www.geeksforgeeks.org/python-time-mktime-method/

    Don't use this directly. Provided for use within this class.
    A platform safe mktime, since unix and upython have slightly different versions
    upython the tuple is (y,m,d,h,m,s,wk,yd)
    Unix python the tuple is (y,m,d,h,m,s,wk,yd,dst)
    0: year: 2000-2060+-?
    1: month: 1-12
    2: day: 1-31
    3: hour:0-23
    4: minute:0-59
    5: sec: 0-61
    6: dow: 0-6. Monday == 0
    7: yd: 1-366
    """
    year = max(year, _EPOCH_YEAR)
    if _isupy:
        return max(0, int(time.mktime((year, month, day, hour, min, sec, None, None))))  # type: ignore [arg-type]
    else:
        return max(0, int(time.mktime((year, month, day, hour, min, sec, -1, -1, -1))))


class TZTime:
    """
    A simpleencapsulated time value, with an optional included TimeZone.
    This is an Immutable class.  All alteration methods return a new instance.
    That allows for easy daisy chaining too.
    The default constructor creates a "now()" instance, based on the system clock.
    It's assumed the system clock creates "zulu/UTC" time instances.  The best way to
    use this class is to in fact have your system clock set to UTC time.
    """

    def __init__(self, t: int | None = None, tz: utimezone.Timezone | None = None):
        """
        Create a new instance of a TZTime object.
        Defaults to now() at Zulu if no args are provided.
        time.time() is used when no t value is provided.
        your system must produce UTC time for this default to be
        effective.
        Use the class TZTime.create() method to create a specific time value.
        """

        # The unix "time" instance
        if t is None:
            self._time: int = int(time.time())
        else:
            assert isinstance(t, int), f"t must be an int, received [{t.__class__}]"
            self._time = t

        # The structured time. Calculated only the 1st time it's needed
        self._stime: time.struct_time | None = None

        # The TimeZone
        self._tz = tz


    @staticmethod
    def now() -> 'TZTime':
        """
        Create an instance of now @ UTC
        """
        return TZTime()


    @staticmethod
    def create(year: int = 0, month: int = 0, day: int = 0, hour: int = 0, min: int = 0, sec: int = 0, tz: utimezone.Timezone | None = None) -> 'TZTime':
        """
        Create a new instance with the given time values, and specific timezone. A None tz is treated like Zulu/UTC

        month: 1-12

        day: 1-31

        hour: 0-23

        min: 0-59

        sec: 0-61
        """
        assert year >= _EPOCH_YEAR, f"Unfortunately, upy has a Jan 1 {_EPOCH_YEAR} Epoch limitation.  Can not create a time with year={year}"
        t = _mktime(year=year, month=month, day=day, hour=hour, min=min, sec=sec)
        return TZTime(t, tz)


    def isDST(self) -> bool:
        """
        Return if this time, and the given timezone, is a DST time or not.
        """
        if self._tz is None:
            return False
        else:
            return self._tz.locIsDST(self._time)


    def isSTD(self) -> bool:
        """
        Returns if this time, and the given timezone, is a STD time or not.
        """
        return not self.isDST()


    def __str__(self) -> str:
        """
        Return the ISO8601 formatted string of this time
        """
        return self.toISO8601()


    def __repr__(self) -> str:
        """
        Return the ISO8601 formatted string of this time
        """
        return self.toISO8601()


    def __eq__(self, other) -> bool:
        """
        [==] Operator
        """
        if not isinstance(other, TZTime):
            return False
        return self.toUTC()._time == other.toUTC()._time

    def __ne__(self, other) -> bool:
        """
        [!=] Operator
        """
        if not isinstance(other, TZTime):
            return False
        return self.toUTC()._time != other.toUTC()._time


    def __gt__(self, other) -> bool:
        """
        [>] Operator
        """
        if not isinstance(other, TZTime):
            return False
        return self.toUTC()._time > other.toUTC()._time


    def __lt__(self, other) -> bool:
        """
        [<] Operator
        """
        if not isinstance(other, TZTime):
            return False
        return self.toUTC()._time < other.toUTC()._time

    def __ge__(self, other) -> bool:
        """
        [>=] Operator
        """
        if not isinstance(other, TZTime):
            return False
        return self.toUTC()._time >= other.toUTC()._time


    def __le__(self, other) -> bool:
        """
        [<=] Operator
        """
        if not isinstance(other, TZTime):
            return False
        return self.toUTC()._time <= other.toUTC()._time


    def _gmtime(self) -> tuple:
        """
        Return the the underlying structured time tuple.
        We fetch the localtime, because on micropython, this is always the same as gmtime due to the lack of tz capacity.
        On unix python, gmtime converts for us, and we dont' want that.  So, localtime it is.
        """
        if self._stime is None:
            self._stime = time.localtime(self._time)
        return self._stime


    def toISO8601(self) -> str:
        """
        Generate a ISO8601 formatted string.
        Use the tz as the Zone designator.  None for Zulu or Local.
        The tz does not convert the time, it adds the correct offset value
        used at the end.
        """

        tz = self.tz()
        if tz is not None:
            offset = 0
            if tz.locIsDST(self._time):
                offset = tz._dst.offset
            else:
                offset = tz._std.offset

            offsetHours = int(offset / 60)
            offsetMinutes = int(offset % 60)
            offsetDir = "+" if offsetHours > 0 else "-"
            offsetHours = abs(offsetHours)
            tzstr = f"{offsetDir}{offsetHours:02d}:{offsetMinutes:02d}"
        else:
            tzstr = "Z"

        iso = f"{self.year():04d}-{self.month():02d}-{self.day():02d}T{self.hour():02d}:{self.minute():02d}:{self.second():02d}{tzstr}"
        return iso



    def year(self) -> int:
        """
        Get the Year
        """
        return self._gmtime()[0]


    def month(self) -> int:
        """
        Get the Month [1-12]
        """
        return self._gmtime()[1]


    def day(self) -> int:
        """
        Get the Day of the Month [1-31]
        """
        return self._gmtime()[2]


    def hour(self) -> int:
        """
        Get the Hour of the Dat 0-23
        """
        return self._gmtime()[3]


    def minute(self) -> int:
        """
        Get the Minute of the Hour [0-59]
        """
        return self._gmtime()[4]


    def second(self) -> int:
        """
        Get the second of the minute [0-59] (actually 0-61 if you account for leap-seconds and the like)
        """
        return self._gmtime()[5]


    def dayOfWeek(self) -> int:
        """
        Get the day of week. 0-6. Mon - Sun)
        """
        return self._gmtime()[6]


    def time(self) -> int:
        """
        Return the raw unix time value. Seconds since EPOCH (Jan 1 2000 on upy devices)
        """
        return self._time


    def tz(self) -> utimezone.Timezone | None:
        """
        Get the TimeZone. Returns None for UTC
        """
        return self._tz


    def toTimezone(self, tz: utimezone.Timezone | None) -> 'TZTime':
        """
        Convert this time, to the new timezone.
        If the new TZ is None, this is converted to UTC.
        This will alter the time to the new TimeZone.
        """
        z = self.toUTC()
        if tz:
            t = tz.toLocal(z._time)
            return TZTime(t, tz)
        else:
            return z


    def toUTC(self) -> 'TZTime':
        """
        convert this time to UTC
        """
        t = self._time
        if self._tz:
            t = self._tz.toUTC(t)
        return TZTime(t, None)


    def secondsBetween(self, other: 'TZTime') -> int:
        """
        return the number of seconds between this, and the other time
        """
        thisZ = self.toUTC()
        otherZ = other.toUTC()
        return otherZ._time - thisZ._time


    def plusYears(self, years: int) -> 'TZTime':
        """
        Add x years to a time value.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0] + years, gm[1], gm[2], gm[3], gm[4], gm[5])
        return TZTime(nt, self._tz)


    def plusMonths(self, months: int) -> 'TZTime':
        """
        Add x months to a time value.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1] + months, gm[2], gm[3], gm[4], gm[5])
        return TZTime(nt, self._tz)


    def plusDays(self, days: int) -> 'TZTime':
        """
        Add x days to a time value.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], gm[2] + days, gm[3], gm[4], gm[5])
        return TZTime(nt, self._tz)


    def plusHours(self, hours: int) -> 'TZTime':
        """
        Add x hours to a time value.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], gm[2], gm[3] + hours, gm[4], gm[5])
        return TZTime(nt, self._tz)


    def plusMinutes(self, minutes: int) -> 'TZTime':
        """
        Add x minutes to a time value.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], gm[2], gm[3], gm[4] + minutes, gm[5])
        return TZTime(nt, self._tz)


    def plusSeconds(self, seconds: int) -> 'TZTime':
        """
        Add x seconds to a time value.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], gm[2], gm[3], gm[4], gm[5] + seconds)
        return TZTime(nt, self._tz)


    def withYear(self, year: int) -> 'TZTime':
        """
        Set the year value
        """
        gm = self._gmtime()
        nt = _mktime(year, gm[1], gm[2], gm[3], gm[4], gm[5])
        return TZTime(nt, self._tz)


    def withMonth(self, month: int) -> 'TZTime':
        """
        Set the month value, can be more than 12, and less than 0, will adjust the year
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], month, gm[2], gm[3], gm[4], gm[5])
        return TZTime(nt, self._tz)


    def withDay(self, day: int) -> 'TZTime':
        """
        Set the Day value. Can be more than 31, and less than 0, will adjust the months.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], day, gm[3], gm[4], gm[5])
        return TZTime(nt, self._tz)


    def withHour(self, hour: int) -> 'TZTime':
        """
        Set the hours value.  Can be more than 24 and less than 0, will adjust the days.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], gm[2], hour, gm[4], gm[5])
        return TZTime(nt, self._tz)


    def withMinute(self, minute: int) -> 'TZTime':
        """
        Set the minutes value. Can be more than 60 and less than 0, will adjust the hours.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], gm[2], gm[3], minute, gm[5])
        return TZTime(nt, self._tz)


    def withSecond(self, second: int) -> 'TZTime':
        """
        Set the seconds value. Can be more than 60 and less than 0, will adjust the minutes.
        """
        gm = self._gmtime()
        nt = _mktime(gm[0], gm[1], gm[2], gm[3], gm[4], second)
        return TZTime(nt, self._tz)


    def withTimezone(self, tz: utimezone.Timezone) -> 'TZTime':
        """
        Sets the timezone, making no changes to the time value.
        You can also clear the timezone to UTC by passing None.
        """
        return TZTime(self._time, tz)
