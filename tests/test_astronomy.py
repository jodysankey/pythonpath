#!/usr/bin/python3

import unittest
from datetime import date, datetime

from dateutil import tz

import astronomy
from astronomy import (DEG_TO_RAD, RAD_TO_DEG, TWO_PI, ONE_AU_IN_KM, Body, Sun, Moon,
                       SphericalCoordinate, EquatorialCoordinate)

# pylint: disable=missing-function-docstring

def deg_min_sec(degrees, minutes, seconds):
    assert(degrees >= 0 and minutes >= 0 and seconds >= 0)
    return degrees + minutes/60.0 + seconds/3600.0

def hr_min_sec(hours, minutes, seconds):
    return hours + minutes/60.0 + seconds/3600.0

class TestAstronomy(unittest.TestCase):
    """Unit tests covering the astonomy module."""

    def test_linear_interpolator(self):
        interp = astronomy.Interpolator([1, 2, 3, 4], [1, 4, 9, 16])
        self.assertAlmostEqual(interp.at(1), 1)
        self.assertAlmostEqual(interp.at(1.5), 2.25)
        self.assertAlmostEqual(interp.at(3.5), 12.25)

    def test_anglular_interpolator(self):
        interp = astronomy.AngularInterpolator([1, 2, 3, 4, 5, 6],
                                               [y*DEG_TO_RAD for y in (315, 45, 135, 225, 315, 45)])
        self.assertAlmostEqual(interp.at(1)*RAD_TO_DEG, 315)
        self.assertAlmostEqual(interp.at(2.5)*RAD_TO_DEG, 90)
        self.assertAlmostEqual(interp.at(5)*RAD_TO_DEG, 315)
        self.assertAlmostEqual(interp.at(3.5)*RAD_TO_DEG, 180)
        self.assertAlmostEqual(interp.at(5.75)*RAD_TO_DEG, 22.5)
        interp = astronomy.AngularInterpolator([1, 2, 3], [y*DEG_TO_RAD for y in (45, 315, 225)])
        self.assertAlmostEqual(interp.at(1.75)*RAD_TO_DEG, 337.5)

    def test_ut_to_datetime(self):
        # Based on the example p61.
        result = astronomy.ut_to_datetime(2436116.25)
        self.assertEqual(result, datetime(1957, 10, 4, 18, 0, 0, tzinfo=tz.UTC))

    def test_datetime_to_ut(self):
        # Based on the example p61.
        result = astronomy.datetime_to_ut(datetime(1957, 10, 4, 18, 0, 0, tzinfo=tz.UTC))
        self.assertAlmostEqual(result, 2436116.25)

    def test_spherical_to_equatorial(self):
        # Example from pp95.
        spherical = SphericalCoordinate(6.684170 * DEG_TO_RAD, 113.215630 * DEG_TO_RAD)
        equatorial = spherical.to_equatorial(23.4392911 * DEG_TO_RAD)
        self.assertAlmostEqual(equatorial.ra * RAD_TO_DEG, 116.328942507)
        self.assertAlmostEqual(equatorial.decl * RAD_TO_DEG, 28.026183126)

    def test_nutation(self):
        # Example of nutation from pp148, modified result by 0.001" since our implementation is
        # the simple IAU expression for mean obliquity and also doesn't include T^2 and T^3 terms.
        delta_psi, mean_obliquity, true_obliquity = astronomy.nutation(2446895.5)
        self.assertAlmostEqual(delta_psi * RAD_TO_DEG, -deg_min_sec(0, 0, 3.86276))
        self.assertAlmostEqual(mean_obliquity * RAD_TO_DEG, deg_min_sec(23, 26, 27.40754))
        self.assertAlmostEqual(true_obliquity * RAD_TO_DEG, deg_min_sec(23, 26, 36.87534))

    def test_greenwich_sidereal_time(self):
        # Example from pp88
        apparent_sidereal_time_rad = astronomy.greenwich_sidereal_time(2446895.5)
        apparent_sidereal_time_hr = apparent_sidereal_time_rad / TWO_PI * 24.0
        self.assertAlmostEqual(apparent_sidereal_time_hr, hr_min_sec(13, 10, 46.13056))
        # Example from pp89
        ut = 2446895.5 + hr_min_sec(19, 21, 0) / 24.0
        apparent_sidereal_time_rad = astronomy.greenwich_sidereal_time(ut)
        apparent_sidereal_time_hr = apparent_sidereal_time_rad / TWO_PI * 24.0
        self.assertAlmostEqual(apparent_sidereal_time_hr, hr_min_sec(8, 34, 56.84829))

    def test_sun_ecliptic_position(self):
        # Example from pp169. Testing only the spherical coordinates since conversion is tested
        # separately.
        spherical, _ = Sun().geocentric_position(2448908.5)
        self.assertAlmostEqual(spherical.lng * RAD_TO_DEG, deg_min_sec(199, 54, 21.93898))
        self.assertAlmostEqual(spherical.lat * RAD_TO_DEG, deg_min_sec(0, 0, 0.6202))
        self.assertAlmostEqual(spherical.rng / ONE_AU_IN_KM, 0.9976077495)

    def test_moon_ecliptic_position(self):
        # Example from pp343.
        spherical, equatorial = Moon().geocentric_position(2448724.5)
        self.assertAlmostEqual(spherical.lng * RAD_TO_DEG, deg_min_sec(133, 10, 2.0397648))
        self.assertAlmostEqual(spherical.lat * RAD_TO_DEG, -deg_min_sec(3, 13, 44.855109))
        self.assertAlmostEqual(spherical.rng, 368409.6848161265)
        self.assertAlmostEqual(equatorial.ra * 24 / TWO_PI, hr_min_sec(8, 58, 45.225115))
        self.assertAlmostEqual(equatorial.decl * RAD_TO_DEG, deg_min_sec(13, 46, 6.15162036))

    def test_moon_phase(self):
        # Example from pp347, expressing an earlier UT to match midnight DT in the example.
        phase, desc, fraction = Moon().phase(datetime(1992, 4, 11, 23, 58, 51, tzinfo=tz.UTC))
        self.assertAlmostEqual(phase * RAD_TO_DEG, 69.07558948833432)
        self.assertEqual(desc, 'waning gibbous')
        self.assertAlmostEqual(fraction, 0.6785679894780358)

    def test_events_from_positions(self):
        # Example from pp103
        venus = Body(-0.5667 * DEG_TO_RAD)
        observer = SphericalCoordinate(42.3333 * DEG_TO_RAD, 71.0833 * DEG_TO_RAD)
        day_num = 2447240.5
        eq_positions = [
            EquatorialCoordinate(40.68021 * DEG_TO_RAD, deg_min_sec(18, 2, 51.4) * DEG_TO_RAD),
            EquatorialCoordinate(41.73129 * DEG_TO_RAD, deg_min_sec(18, 26, 27.3) * DEG_TO_RAD),
            EquatorialCoordinate(42.78204 * DEG_TO_RAD, deg_min_sec(18, 49, 38.7) * DEG_TO_RAD),
        ]
        events = venus._events_from_positions(eq_positions, day_num - 1.0, observer)
        expected_events = [
            (day_num + 0.12129311, 'set'),
            (day_num + 0.51765558, 'rise'),
            (day_num + 0.81979427, 'transit'),
        ]
        self.assertEqual(len(events), len(expected_events))
        for actual, expected in zip(events, expected_events):
            self.assertEqual(actual[1], expected[1])
            self.assertAlmostEqual(actual[0], expected[0])

    def test_events(self):
        # San Francisco
        observer = SphericalCoordinate(deg_min_sec(37, 46, 0) * DEG_TO_RAD,
                                       deg_min_sec(122, 25, 0) * DEG_TO_RAD)
        events = Sun().events(date(2020, 7, 2), date(2020, 7, 3), observer)
        # Truncate the seconds for ease of comparison
        truncated_events = [(evt[0].replace(microsecond=0), evt[1]) for evt in events]
        # Verified this data to the minute level with NOAA ESRL sunrise/sunset calculator.
        expected_events = [
            (datetime(2020, 7, 2, 3, 35, 26, tzinfo=tz.UTC), 'set'),
            (datetime(2020, 7, 2, 12, 52, 16, tzinfo=tz.UTC), 'rise'),
            (datetime(2020, 7, 2, 20, 13, 53, tzinfo=tz.UTC), 'transit'),
            (datetime(2020, 7, 3, 3, 35, 19, tzinfo=tz.UTC), 'set'),
            (datetime(2020, 7, 3, 12, 52, 47, tzinfo=tz.UTC), 'rise'),
            (datetime(2020, 7, 3, 20, 14, 4, tzinfo=tz.UTC), 'transit'),
        ]
        self.assertEqual(truncated_events, expected_events)


if __name__ == '__main__':
    unittest.main()
