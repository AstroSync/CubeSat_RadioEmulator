from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Literal
import numpy as np
from pytz import utc
from skyfield.api import load
from skyfield.units import Angle, Distance, AngleRate, Velocity
from skyfield.vectorlib import VectorSum
from skyfield.positionlib import Geocentric
from skyfield.sgp4lib import EarthSatellite
from skyfield.timelib import Time, Timescale
from skyfield.toposlib import wgs84, GeographicPosition



class SatellitePath:
    def __init__(self, sat_name: str, altitude: Angle, azimute: Angle, distance: Distance,
                 alt_rate: AngleRate, az_rate: AngleRate, dist_rate: Velocity, time_points: list[datetime]) -> None:
        self.sat_name: str = sat_name
        self.altitude: np.ndarray = altitude.degrees  # type: ignore
        self.azimuth: np.ndarray = azimute.degrees  # type: ignore
        self.dist: np.ndarray = distance.km  # type: ignore
        self.alt_rate: np.ndarray = alt_rate.degrees.per_second  # type: ignore
        self.az_rate: np.ndarray = az_rate.degrees.per_second  # type: ignore
        self.dist_rate: np.ndarray = dist_rate.km_per_s  # type: ignore
        self.t_points: list[datetime] = time_points
        self._index: int = 0
        # 1 - 'up', -1 - 'down'
        self.az_rotation_direction: Literal[1, -1] = -1 + 2 * (self.azimuth[1] > self.azimuth[0])  # type: ignore
        self._max_altitude = np.max(self.altitude)  # type: ignore

    def find_nearest(self, array: np.ndarray, timestamp: datetime) -> int | float:
        idx: int = (np.abs(np.asarray(self.t_points) - timestamp)).argmin()
        return array[idx]

    def get_max_elevation(self) -> float:
        return self._max_altitude

    def to_dict(self) -> dict:
        length: int = len(self.altitude)

        def to_string(data) -> str:
            return f'[{float(data[0]):.2f}, ..., {float(data[length//2]):.2f}, ..., {float(data[-1]):.2f}]'

        return {
            'alt':          to_string(self.altitude),
            'az':           to_string(self.azimuth),
            'dist':         to_string(self.dist),
            'alt_rate':     to_string(self.alt_rate),
            'az_rate':      to_string(self.az_rate),
            'dist_rate':    to_string(self.dist_rate),
            't_points':     f'[{self.t_points[0]}, ..., {self.t_points[-1]}]',
            'az_rotation_direction': int(self.az_rotation_direction)
        }

    def __repr__(self) -> str:
        return f'Altitude deg from {self.altitude[0]:.2f} to {self.altitude[-1]:.2f}\n' \
               f'Azimuth deg from {self.azimuth[0]:.2f} to {self.azimuth[-1]:.2f}\n' \
               f'Distance km from {self.dist.min():.2f} to {self.dist.max():.2f}\n' \
               f'Altitude rate deg/s from {self.alt_rate.min():.2f} to {self.alt_rate.max():.2f}\n' \
               f'Azimuth rate deg/s from {self.az_rate.min():.2f} to {self.az_rate.max():.2f}\n' \
               f'Distance rate km/s from {self.dist_rate.min():.2f} to {self.dist_rate.max():.2f}\n' \
               f'Time points: from {self.t_points[0]} to {self.t_points[-1]}.\n' \
               f'Duration: {(self.t_points[-1] - self.t_points[0]).seconds} sec\n'

    def __getitem__(self, key):
        return (self.altitude[key], self.azimuth[key], self.t_points[key])

    def __iter__(self):
        return self

    def __next__(self) -> tuple[float, float, datetime]:
        if self._index < len(self.altitude):
            var: tuple[float, float, datetime] = (self.altitude[self._index], self.azimuth[self._index],
                    self.t_points[self._index])
            self._index += 1
            return var
        raise StopIteration


class TestSatellitePath(SatellitePath):

    def __init__(self, test_size: int = 45) -> None:
        self.sat_name: str = 'test_sat'
        self.altitude: np.ndarray = np.linspace(0.0, test_size, num=test_size)
        self.azimuth: np.ndarray = np.linspace(90.0, 90 + test_size, num=test_size)
        self.dist: np.ndarray = np.zeros(test_size)
        self.alt_rate: np.ndarray = np.ones(test_size)
        self.az_rate: np.ndarray = np.ones(test_size)
        self.dist_rate: np.ndarray = np.zeros(test_size)
        self.az_rotation_direction: int = 1
        self.t_points: list[datetime] = [datetime.now().astimezone(utc) + timedelta(seconds=6 + x)
                                         for x in range(test_size)]
        self._index: int = 0
        self._max_altitude = 0


def angle_points(tle: str, sat: str, observer: GeographicPosition, t_1: datetime, t_2: datetime,
                 sampling_rate=3.3333) -> SatellitePath:
    timescale: Timescale = load.timescale()
    time_points: Time = timescale.linspace(timescale.from_datetime(t_1), timescale.from_datetime(t_2),
                                           int((t_2 - t_1).seconds * sampling_rate))
    tle_strings: list[str] = tle.split('\n')
    satellite: EarthSatellite = EarthSatellite(name=tle_strings[0], line1=tle_strings[1], line2=tle_strings[2])

    sat_position: VectorSum = satellite - observer
    topocentric: Geocentric = sat_position.at(time_points)  # type: ignore
    return SatellitePath(sat, *topocentric.frame_latlon_and_rates(observer), time_points.utc_datetime())  # type: ignore

if __name__ == '__main__':
    start_time_: datetime = datetime.now(tz=timezone.utc)
    # points: SatellitePath = angle_points('NORBI', wgs84.latlon(60.006770, 30.379205, 40),
    #                                      datetime.fromisoformat('2023-03-29T13:46:47.000+00:00'),
    #                                      datetime.fromisoformat('2023-03-29T13:46:47.000+00:00') +
    #                                       timedelta(seconds=315))
    # print(points)
    print(wgs84.latlon(float(os.environ.get('LATITUDE', 60.006770)),
                                                         float(os.environ.get('LONGITUDE', 30.379205)),
                                                         float(os.environ.get('ELEVATION', 40.0))).elevation.m)
    #for alt, az, t_point in points:
    #    print(alt, az, t_point)
