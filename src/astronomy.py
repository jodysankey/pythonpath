"""Collection of astronomy routines that can caluculate positions and phases of the sun and moon.
The implementation is based on my earlier C++ implementation from ~2009, which in turn is based on
the algorithms provided in "Astronomical Algorithms" by Jean Meeus. It's a great book. You should
buy it."""

#==============================================================
# Copyright Jody M Sankey 2020
#
# This software may be modified and distributed under the terms
# of the MIT license. See the LICENCE.md file for details.
#==============================================================
# PublicPermissions: True
#==============================================================

from datetime import datetime, date, time, timedelta
from math import sin, cos, tan, asin, acos, atan2, pi, floor
from dateutil import tz 
from scipy import interpolate

# In many case we wish to use standard abbreviations that contain capitals or are less than
# three characters, and align columns in the data matrices. Disable pylint warnings for these.
# pylint: disable=bad-whitespace,invalid-name

SEC_IN_DAY = 86400.0
DEG_TO_RAD = pi / 180.0
RAD_TO_DEG = 180.0 / pi
TWO_PI = 2 * pi
ONE_AU_IN_KM = 149597870.7

# Add to datetime.date.ordinal to calculate the Julian day.
JD_OFFSET = 1721424.5


# Define the sun and moon matrices, thanks to PJ Naughter (Web: www.naughter.com) for typing
# these in originally.

# Sun position data.

L0 = (
    ( 175347046, 0,         0 ),
    ( 3341656,   4.6692568, 6283.0758500 ),
    ( 34894,     4.62610,   12566.15170 ),
    ( 3497,      2.7441,    5753.3849 ),
    ( 3418,      2.8289,    3.5231 ),
    ( 3136,      3.6277,    77713.7715 ),
    ( 2676,      4.4181,    7860.4194 ),
    ( 2343,      6.1352,    3930.2097 ),
    ( 1324,      0.7425,    11506.7698 ),
    ( 1273,      2.0371,    529.6910 ),
    ( 1199,      1.1096,    1577.3435 ),
    ( 990,       5.233,     5884.927 ),
    ( 902,       2.045,     26.298 ),
    ( 857,       3.508,     398.149 ),
    ( 780,       1.179,     5223.694 ),
    ( 753,       2.533,     5507.553 ),
    ( 505,       4.583,     18849.228 ),
    ( 492,       4.205,     775.523 ),
    ( 357,       2.920,     0.067 ),
    ( 317,       5.849,     11790.629 ),
    ( 284,       1.899,     796.288 ),
    ( 271,       0.315,     10977.079 ),
    ( 243,       0.345,     5486.778 ),
    ( 206,       4.806,     2544.314 ),
    ( 205,       1.869,     5573.143 ),
    ( 202,       2.458,     6069.777 ),
    ( 156,       0.833,     213.299 ),
    ( 132,       3.411,     2942.463 ),
    ( 126,       1.083,     20.775 ),
    ( 115,       0.645,     0.980 ),
    ( 103,       0.636,     4694.003 ),
    ( 102,       0.976,     15720.839 ),
    ( 102,       4.267,     7.114 ),
    ( 99,        6.21,      2146.17 ),
    ( 98,        0.68,      155.42 ),
    ( 86,        5.98,      161000.69 ),
    ( 85,        1.30,      6275.96 ),
    ( 85,        3.67,      71430.70 ),
    ( 80,        1.81,      17260.15 ),
    ( 79,        3.04,      12036.46 ),
    ( 75,        1.76,      5088.63 ),
    ( 74,        3.50,      3154.69 ),
    ( 74,        4.68,      801.82 ),
    ( 70,        0.83,      9437.76 ),
    ( 62,        3.98,      8827.39 ),
    ( 61,        1.82,      7084.90 ),
    ( 57,        2.78,      6286.60 ),
    ( 56,        4.39,      14143.50 ),
    ( 56,        3.47,      6279.55 ),
    ( 52,        0.19,      12139.55 ),
    ( 52,        1.33,      1748.02 ),
    ( 51,        0.28,      5856.48 ),
    ( 49,        0.49,      1194.45 ),
    ( 41,        5.37,      8429.24 ),
    ( 41,        2.40,      19651.05 ),
    ( 39,        6.17,      10447.39 ),
    ( 37,        6.04,      10213.29 ),
    ( 37,        2.57,      1059.38 ),
    ( 36,        1.71,      2352.87 ),
    ( 36,        1.78,      6812.77 ),
    ( 33,        0.59,      17789.85 ),
    ( 30,        0.44,      83996.85 ),
    ( 30,        2.74,      1349.87 ),
    ( 25,        3.16,      4690.48 ))

L1 = (
    ( 628331966747.0, 0,          0 ),
    ( 206059,         2.678235,   6283.075850 ),
    ( 4303,           2.6351,     12566.1517 ),
    ( 425,            1.590,      3.523 ),
    ( 119,            5.796,      26.298 ),
    ( 109,            2.966,      1577.344 ),
    ( 93,             2.59,       18849.23 ),
    ( 72,             1.14,       529.69 ),
    ( 68,             1.87,       398.15 ),
    ( 67,             4.41,       5507.55 ),
    ( 59,             2.89,       5223.69 ),
    ( 56,             2.17,       155.42 ),
    ( 45,             0.40,       796.30 ),
    ( 36,             0.47,       775.52 ),
    ( 29,             2.65,       7.11 ),
    ( 21,             5.43,       0.98 ),
    ( 19,             1.85,       5486.78 ),
    ( 19,             4.97,       213.30 ),
    ( 17,             2.99,       6275.96 ),
    ( 16,             0.03,       2544.31 ),
    ( 16,             1.43,       2146.17 ),
    ( 15,             1.21,       10977.08 ),
    ( 12,             2.83,       1748.02 ),
    ( 12,             3.26,       5088.63 ),
    ( 12,             5.27,       1194.45 ),
    ( 12,             2.08,       4694.00 ),
    ( 11,             0.77,       553.57 ),
    ( 10,             1.30,       6286.60 ),
    ( 10,             4.24,       1349.87 ),
    ( 9,              2.70,       242.73 ),
    ( 9,              5.64,       951.72 ),
    ( 8,              5.30,       2352.87 ),
    ( 6,              2.65,       9437.76 ),
    ( 6,              4.67,       4690.48 ))

L2 = (
    ( 52919,  0,      0 ),
    ( 8720,   1.0721, 6283.0758 ),
    ( 309,    0.867,  12566.152 ),
    ( 27,     0.05,   3.52 ),
    ( 16,     5.19,   26.30 ),
    ( 16,     3.68,   155.42 ),
    ( 10,     0.76,   18849.23 ),
    ( 9,      2.06,   77713.77 ),
    ( 7,      0.83,   775.52 ),
    ( 5,      4.66,   1577.34 ),
    ( 4,      1.03,   7.11 ),
    ( 4,      3.44,   5573.14 ),
    ( 3,      5.14,   796.30 ),
    ( 3,      6.05,   5507.55 ),
    ( 3,      1.19,   242.73 ),
    ( 3,      6.12,   529.69 ),
    ( 3,      0.31,   398.15 ),
    ( 3,      2.28,   553.57 ),
    ( 2,      4.38,   5223.69 ),
    ( 2,      3.75,   0.98 ))

L3 = (
    ( 289, 5.844, 6283.076 ),
    ( 35,  0,     0 ),
    ( 17,  5.49,  12566.15 ),
    ( 3,   5.20,  155.42 ),
    ( 1,   4.72,  3.52 ),
    ( 1,   5.30,  18849.23 ),
    ( 1,   5.97,  242.73 ))

L4 = (
    ( 114, 3.142,  0 ),
    ( 8,   4.13,   6283.08 ),
    ( 1,   3.84,   12566.15 ))

L5 = (( 1, 3.14, 0 ),)

B0 = (
    ( 280, 3.199, 84334.662 ),
    ( 102, 5.422, 5507.553 ),
    ( 80,  3.88,  5223.69),
    ( 44,  3.70,  2352.87 ),
    ( 32,  4.00,  1577.34 ))

B1 = (
    ( 9, 3.90, 5507.55 ),
    ( 6, 1.73, 5223.69))

B2 = (
    ( 22378, 3.38509, 10213.28555 ),
    ( 282,   0,       0 ),
    ( 173,   5.256,   20426.571 ),
    ( 27,    3.87,    30639.86 ))

B3 = (
    ( 647, 4.992, 10213.286 ),
    ( 20,  3.14,  0 ),
    ( 6,   0.77,  20426.57 ),
    ( 3,   5.44,  30639.86 ))

B4 = (( 14, 0.32, 10213.29 ),)

R0 = (
    ( 100013989,  0,          0 ),
    ( 1670700,    3.0984635,  6283.0758500 ),
    ( 13956,      3.05525,    12566.15170 ),
    ( 3084,       5.1985,     77713.7715 ),
    ( 1628,       1.1739,     5753.3849 ),
    ( 1576,       2.8469,     7860.4194 ),
    ( 925,        5.453,      11506.770 ),
    ( 542,        4.564,      3930.210 ),
    ( 472,        3.661,      5884.927 ),
    ( 346,        0.964,      5507.553 ),
    ( 329,        5.900,      5223.694 ),
    ( 307,        0.299,      5573.143 ),
    ( 243,        4.273,      11790.629 ),
    ( 212,        5.847,      1577.344 ),
    ( 186,        5.022,      10977.079 ),
    ( 175,        3.012,      18849.228 ),
    ( 110,        5.055,      5486.778 ),
    ( 98,         0.89,       6069.78 ),
    ( 86,         5.69,       15720.84 ),
    ( 86,         1.27,       161000.69),
    ( 65,         0.27,       17260.15 ),
    ( 63,         0.92,       529.69 ),
    ( 57,         2.01,       83996.85 ),
    ( 56,         5.24,       71430.70 ),
    ( 49,         3.25,       2544.31 ),
    ( 47,         2.58,       775.52 ),
    ( 45,         5.54,       9437.76 ),
    ( 43,         6.01,       6275.96 ),
    ( 39,         5.36,       4694.00 ),
    ( 38,         2.39,       8827.39 ),
    ( 37,         0.83,       19651.05 ),
    ( 37,         4.90,       12139.55 ),
    ( 36,         1.67,       12036.46 ),
    ( 35,         1.84,       2942.46 ),
    ( 33,         0.24,       7084.90 ),
    ( 32,         0.18,       5088.63 ),
    ( 32,         1.78,       398.15 ),
    ( 28,         1.21,       6286.60 ),
    ( 28,         1.90,       6279.55 ),
    ( 26,         4.59,       10447.39 )
)

R1 = (
    ( 103019, 1.107490, 6283.075850 ),
    ( 1721,   1.0644,   12566.1517 ),
    ( 702,    3.142,    0 ),
    ( 32,     1.02,     18849.23 ),
    ( 31,     2.84,     5507.55 ),
    ( 25,     1.32,     5223.69 ),
    ( 18,     1.42,     1577.34 ),
    ( 10,     5.91,     10977.08 ),
    ( 9,      1.42,     6275.96 ),
    ( 9,      0.27,     5486.78 ))

R2 = (
    ( 4359, 5.7846, 6283.0758 ),
    ( 124,  5.579,  12566.152 ),
    ( 12,   3.14,   0 ),
    ( 9,    3.63,   77713.77 ),
    ( 6,    1.87,   5573.14 ),
    ( 3,    5.47,   18849.23 ))

R3 = (
    ( 145,  4.273,  6283.076 ),
    ( 7,    3.92,   12566.15 ))

R4 = (( 4, 2.56, 6283.08 ),)


# Moon position data.

arguments_LR = ( 
  ( 0, 0,  1,  0 ),
  ( 2, 0,  -1, 0 ),
  ( 2, 0,  0,  0 ),
  ( 0, 0,  2,  0 ),
  ( 0, 1,  0,  0 ),
  ( 0, 0,  0,  2 ),
  ( 2, 0,  -2, 0 ),
  ( 2, -1, -1, 0 ),
  ( 2, 0,  1,  0 ),
  ( 2, -1, 0,  0 ),
  ( 0, 1,  -1, 0 ),
  ( 1, 0,  0,  0 ),
  ( 0, 1,  1,  0 ),
  ( 2, 0,  0,  -2 ),
  ( 0, 0,  1,  2 ),
  ( 0, 0,  1,  -2 ),
  ( 4, 0,  -1, 0 ),
  ( 0, 0,  3,  0 ),
  ( 4, 0,  -2, 0 ),
  ( 2, 1,  -1, 0 ),
  ( 2, 1,  0,  0 ),
  ( 1, 0,  -1, 0 ),
  ( 1, 1,  0,  0 ),
  ( 2, -1, 1,  0 ),
  ( 2, 0,  2,  0 ),
  ( 4, 0,  0,  0 ),
  ( 2, 0,  -3, 0 ),
  ( 0, 1,  -2, 0 ),
  ( 2, 0,  -1, 2 ),
  ( 2, -1, -2, 0 ),
  ( 1, 0,  1,  0 ),
  ( 2, -2, 0,  0 ),
  ( 0, 1,  2,  0 ),
  ( 0, 2,  0,  0 ),
  ( 2, -2, -1, 0 ),
  ( 2, 0,  1,  -2 ),
  ( 2, 0,  0,  2 ),
  ( 4, -1, -1, 0 ),
  ( 0, 0,  2,  2 ),
  ( 3, 0,  -1, 0 ),
  ( 2, 1,  1,  0 ),
  ( 4, -1, -2, 0 ),
  ( 0, 2,  -1, 0 ),
  ( 2, 2,  -1, 0 ),
  ( 2, 1,  -2, 0 ),
  ( 2, -1, 0,  -2 ),
  ( 4, 0,  1,  0 ),
  ( 0, 0,  4,  0 ),
  ( 4, -1, 0,  0 ),
  ( 1, 0,  -2, 0 ),
  ( 2, 1,  0,  -2 ),
  ( 0, 0,  2,  -2 ),
  ( 1, 1,  1,  0 ),
  ( 3, 0,  -2, 0 ),
  ( 4, 0,  -3, 0 ),
  ( 2, -1, 2,  0 ),
  ( 0, 2,  1,  0 ),
  ( 1, 1,  -1, 0 ),
  ( 2, 0,  3,  0 ),
  ( 2, 0,  -1, -2 )
)
   
coefficients_LR = ( 
  ( 6288774,  -20905355 ),
  ( 1274027,  -3699111 ),
  ( 658314,   -2955968 ),
  ( 213618,   -569925 ),
  ( -185116,  48888 ),
  ( -114332,  -3149 ),
  ( 58793,    246158 ),
  ( 57066,    -152138 ),
  ( 53322,    -170733 ),
  ( 45758,    -204586 ),
  ( -40923,   -129620 ),
  ( -34720,   108743 ),
  ( -30383,   104755 ),
  ( 15327,    10321 ),
  ( -12528,   0 ),
  ( 10980,    79661 ),
  ( 10675,    -34782 ),
  ( 10034,    -23210 ),
  ( 8548,     -21636 ),
  ( -7888,    24208 ),
  ( -6766,    30824 ),
  ( -5163,    -8379 ),
  ( 4987,     -16675 ),
  ( 4036,     -12831 ),
  ( 3994,     -10445 ),
  ( 3861,     -11650 ),
  ( 3665,     14403 ),
  ( -2689,    -7003 ),
  ( -2602,    0 ), 
  ( 2390,     10056 ),
  ( -2348,    6322 ),
  ( 2236,     -9884 ),
  ( -2120,    5751 ),
  ( -2069,    0 ),
  ( 2048,     -4950 ),
  ( -1773,    4130 ),
  ( -1595,    0 ),
  ( 1215,     -3958 ),
  ( -1110,    0 ),
  ( -892,     3258 ),
  ( -810,     2616 ),
  ( 759,     -1897 ),
  ( -713,     -2117 ),
  ( -700,     2354 ),
  ( 691,      0 ),
  ( 596,      0 ),
  ( 549,      -1423 ),
  ( 537,      -1117 ),
  ( 520,      -1571 ),
  ( -487,     -1739 ),
  ( -399,     0 ),
  ( -381,     -4421 ),
  ( 351,      0 ),
  ( -340,     0 ),
  ( 330,      0 ) ,
  ( 327,      0 ),
  ( -323,     1165 ),
  ( 299,      0 ),
  ( 294,      0 ),
  ( 0,        8752 )
)

arguments_B = ( 
  ( 0, 0,  0,  1  ),
  ( 0, 0,  1,  1  ),
  ( 0, 0,  1,  -1  ),
  ( 2, 0,  0,  -1  ),
  ( 2, 0,  -1, 1  ),
  ( 2, 0,  -1, -1 ),
  ( 2, 0,  0,  1  ),
  ( 0, 0,  2,  1 ),
  ( 2, 0,  1,  -1  ),
  ( 0, 0,  2,  -1 ),
  ( 2, -1, 0,  -1 ),
  ( 2, 0,  -2, -1 ),
  ( 2, 0,  1,  1 ),
  ( 2, 1,  0,  -1  ),
  ( 2, -1, -1, 1 ),
  ( 2, -1, 0,  1  ),
  ( 2, -1, -1, -1  ),
  ( 0, 1,  -1, -1 ),
  ( 4, 0,  -1, -1  ) ,
  ( 0, 1,  0,  1  ),
  ( 0, 0,  0,  3 ),
  ( 0, 1,  -1, 1  ),
  ( 1, 0,  0,  1 ),
  ( 0, 1,  1,  1,  ),
  ( 0, 1,  1,  -1  ),
  ( 0, 1,  0,  -1  ),
  ( 1, 0,  0,  -1  ),
  ( 0, 0,  3,  1  ),
  ( 4, 0,  0,  -1  ),
  ( 4, 0,  -1, 1, ),
  ( 0, 0,  1,  -3 ),
  ( 4, 0,  -2, 1  ),
  ( 2, 0,  0,  -3 ),
  ( 2, 0,  2,  -1 ),
  ( 2, -1, 1,  -1 ),
  ( 2, 0,  -2, 1  ),
  ( 0, 0,  3,  -1 ),
  ( 2, 0,  2,  1  ),
  ( 2, 0,  -3, -1 ),
  ( 2, 1,  -1, 1  ),
  ( 2, 1,  0,  1  ),
  ( 4, 0,  0,  1  ),
  ( 2, -1, 1,  1  ),
  ( 2, -2, 0,  -1 ),
  ( 0, 0,  1,  3  ),
  ( 2, 1,  1,  -1 ),
  ( 1, 1,  0,  -1 ),
  ( 1, 1,  0,  1  ),
  ( 0, 1,  -2, -1 ),
  ( 2, 1,  -1, -1 ),
  ( 1, 0,  1,  1  ),
  ( 2, -1, -2, -1 ),
  ( 0, 1,  2,  1  ),
  ( 4, 0,  -2, -1 ),
  ( 4, -1, -1, -1 ),
  ( 1, 0,  1,  -1 ),
  ( 4, 0,  1,  -1 ),
  ( 1, 0,  -1, -1 ),
  ( 4, -1, 0,  -1 ),
  ( 2, -2, 0,  1  ),
)

coefficients_B = (
  5128122, 280602,  277693,  173237,  55413,   46271,   32573,   17198,   9266,    8822,
  8216,    4324,    4200,    -3359,   2463,    2211,    2065,    -1870,   1828,    -1794,
  -1749,   -1565,   -1491,   -1475,   -1410,   -1344,   -1335,   1107,    1021,    833,
  777,     671,     607,     596,     491,     -451,    439,     422,     421,     -366,  
  -351,    331,     315,     302,     -283,    -229,    223,     223,     -220,    -220,
  -185,    181,     -177,    176,     166,     -164,    132,     -119,    115,     107,  
)


def ut_to_dt(ut):
    """Converts a universal time in days to a dynamical time in days."""
    # As at July 2020, TAI is 37 sec ahead of UTC, TDT is 32.184 seconds ahead of TAI.
    return ut + 69.184/SEC_IN_DAY


def ut_to_datetime(ut):
    """Convert a universal time in days to a UTC datetime.datetime object."""
    days_after_origin = ut - JD_OFFSET
    return (datetime.combine(date.fromordinal(floor(days_after_origin)), time.min, tzinfo=tz.UTC)
        + timedelta(days=1) * (days_after_origin % 1.0))


def datetime_to_ut(datetime):
    """Convert a tzaware datetime.datetime object to a universal time in days."""
    utc = datetime.astimezone(tz.UTC)
    days = utc.date().toordinal()
    fraction = (utc - datetime.combine(utc.date(), time.min, tz.UTC)) / timedelta(days=1)
    return JD_OFFSET + days + fraction


def nutation(dt):
    """Return deltas_psi, mean_obliquity, and true_obliquity for the Earth's nutation at a
    given dynamical time."""
    # Astromonical Algorithms pp147

    # Time in centuries
    T = (dt - 2451545.0)/36525.0
    # Longitude of the ascending node of the moons mean orbit
    omega = (125.04452 - 1934.136261 * T + 0.0020708 * T * T + T * T * T / 450000) * DEG_TO_RAD
    # Mean longitude of the sun
    L = (280.4665 + 36000.7698 * T) * DEG_TO_RAD
    # Mean longitude of the moon
    L_dash = (218.3165 + 481267.8813 * T) * DEG_TO_RAD
    # Nutation in longitude
    delta_psi = (-17.20 * sin(omega) - 1.32 * sin(2.0 * L) - 0.23 * sin(2.0 * L_dash)
                 + 0.21 * sin(2 * omega)) * DEG_TO_RAD / 3600.0
    # Mean obliquity of the ecliptic
    mean_obliquity = (23.43929111111 - 0.01300416667 * T - 1.638888889e-7 * T * T
                      + 5.03611111e-7 * T * T * T) * DEG_TO_RAD
    # Nutation in obliquity
    nut_obl = (9.2 * cos(omega) + 0.57 * cos(2.0 * L) + 0.1 * cos(2.0 * L_dash)
               - 0.09 * cos(2 * omega)) * DEG_TO_RAD / 3600.0
    true_obliquity = mean_obliquity + nut_obl

    return (delta_psi, mean_obliquity, true_obliquity)


def greenwich_sidereal_time(ut):
    """Returns the Greewich sidereal time for a specified universal time."""
    # pp88 Astronomical Algorithms

    # Equation 12.4 was not maintaining sufficient numeric precision
    # so need to calculate the sidereal time at midnight and then offset

    # Julian day at midnight.
    day = floor(ut - 0.5) + 0.5
    # Fraction of the day.
    frac = (ut - 0.5) % 1.0
    # Time in centuries
    T = (day - 2451545.0) / 36525.0
    # Sidereal time at midnight
    theta0 = ((100.46061837 + 36000.770053608 * T + 0.000387933 * T * T -
               T * T * T / 38710000.0) * DEG_TO_RAD) % TWO_PI
    theta0 += 1.00273790935 * frac * TWO_PI

    # Get nutation and correct to apparent (pp144)
    delta_psi, _, epsilon = nutation(ut_to_dt(ut))
    theta0 = (theta0 + delta_psi * cos(epsilon)) % TWO_PI
    return theta0


class SphericalCoordinate:
    """A spherical coordinate, expressed as latitude and longitude in radians with an optional
    range in kilometers."""
    def __init__(self, latitude, longitude, range_km=None):
        self.lat = latitude
        self.lng = longitude
        self.rng = range_km
    
    def to_equatorial(self, epsilon):
        """Returns a corresponding EquatorialCoordinate, given the obliquity (epsilon)
        from a nutation calculation."""
        ra = atan2(sin(self.lng) * cos(epsilon) - tan(self.lat) * sin(epsilon), cos(self.lng))
        decl = asin(sin(self.lat) * cos(epsilon) + cos(self.lat) * sin(epsilon) * sin(self.lng))
        return EquatorialCoordinate(ra, decl)
   

class EquatorialCoordinate:
    """An equatorial coordinate, expressed as declination and right ascension in radians."""
    def __init__(self, right_ascension, declination):
        self.ra = right_ascension
        self.decl = declination


class Interpolator:
    """A convenient object oriented wrapper around the cubic interpolation provided by scipy."""
    def __init__(self, x_values, y_values):
        self.interp = interpolate.splrep(x_values, y_values, k=min(3, len(x_values)-1))

    def at(self, x):
        """Returns the interpolated y value at position x."""
        return interpolate.splev([x], self.interp)[0]


class AngularInterpolator:
    """A cubic interpolator over y values that have be folded into the range [0, 2*PI>."""
    def __init__(self, x_values, y_values):
        # Need to unfold any y values that look like they span the max or min limit.
        clean_y_values = []
        for y in y_values:
            if clean_y_values:
                while clean_y_values[-1] - y > pi:
                    y += 2*pi
                while y - clean_y_values[-1] > pi:
                    y -= 2*pi
            clean_y_values.append(y)
        self.interp = interpolate.splrep(x_values, clean_y_values, k=min(3, len(x_values)-1))

    def at(self, x):
        """Returns the interpolated y value at position x."""
        return interpolate.splev([x], self.interp)[0] % TWO_PI


class Body:
    """General calculations for an astronomical body."""
    def __init__(self, apparent_altitude):
        # The apparent altitude at which the body sets and rises, in radians.
        self.apparent_altitude = apparent_altitude

    def events(self, min_date, max_date, observer):
        """Calculates the rise, transit, and set times within the specified UTC dates using the
        latitude and longitude supplied in observer, returning as a list of (datetime, event_type)
        tuples where event_type is 'rise', 'transit', or 'set' and all datetimes are in UTC."""

        # Always calculate an extra day each side to allow interpolation - a date range of a single
        # date uses 3 points: the midnights at the start of the date plus 2 additional ones.
        first_midnight = min_date.toordinal() - 1 + JD_OFFSET
        ut_midnights = [first_midnight + i for i in range((max_date - min_date).days + 3)]

        # Call a method each body should implement to calculate the position.
        eq_positions = [self.geocentric_position(ut_to_dt(ut))[1] for ut in ut_midnights]
        # Farm out most of the work to a function working in ut we can test with a book example.
        events = self._events_from_positions(eq_positions, first_midnight, observer)
        # Convert into datetimes.
        return [(ut_to_datetime(event[0]), event[1]) for event in events]
 

    def _events_from_positions(self, equatorial_positions, start_midnight, observer):
        """Given a list of equatorial positions for the body on sequential midnights in UT, starting
        at start_midnight, calculates the rise, transit, and set times for all days except the first
        and last, using the latitude and longitude supplied in observer, returning as a list of
        (ut, event_type) tuples where event_type is 'rise', 'transit', or 'set'."""

        # Based on the algorithm in Astronomical Algoriths, pp101
        output = []

        # Set up spline interpolation on the equatorial elements.
        midnights = [start_midnight + i for i in range(len(equatorial_positions))]
        decl_interp = Interpolator(midnights, [eq.decl for eq in equatorial_positions])
        ra_interp = AngularInterpolator(midnights, [eq.ra for eq in equatorial_positions])

        # Iterate through the non-start/end days where we have enough data to interpolate.
        for i in range(1, len(equatorial_positions) - 1):
            eq = equatorial_positions[i]
            midnight = midnights[i]

            # Check the object actually passes the horizon
            cos_H0 = ((sin(self.apparent_altitude) - (sin(observer.lat) * sin(eq.decl)))
                      / (cos(observer.lat) * cos(eq.decl)))
            if cos_H0 < -1.0 or cos_H0 > 1.0:
                # Object must never rise or set, don't add events for this day (not even transit).
                continue

            # First get approximate times
            theta0 = greenwich_sidereal_time(midnight)
            H0 = acos(cos_H0)
            transit = (eq.ra + observer.lng - theta0) / TWO_PI % 1.0
            rise = (transit - H0 / TWO_PI) % 1.0
            set_ = (transit + H0 / TWO_PI) % 1.0

            # Then correct a few times to improve
            for _ in range(3):
                # Transit
                alpha = ra_interp.at(midnight + transit)
                H = theta0 + 6.30038809259 * transit - observer.lng - alpha
                if H > pi:
                    H -= TWO_PI
                elif H < -pi:
                    H += TWO_PI
                transit = (transit - H/TWO_PI) % 1.0

                # Rising
                alpha = ra_interp.at(midnight + rise)
                delta = decl_interp.at(midnight + rise)

                H = theta0 + 6.30038809259 * rise - observer.lng - alpha
                h = asin(sin(delta) * sin(observer.lat) + cos(observer.lat) * cos(delta) * cos(H))
                rise = (rise + (h - self.apparent_altitude)
                        / (TWO_PI * cos(delta) * cos(observer.lat) * sin(H))) % 1.0

                # Setting
                alpha = ra_interp.at(midnight + set_)
                delta = decl_interp.at(midnight + set_)

                H = theta0 + 6.30038809259 * set_ - observer.lng - alpha
                h = asin(sin(delta) * sin(observer.lat) + cos(observer.lat) * cos(delta) * cos(H))
                set_ = (set_ + (h - self.apparent_altitude)
                        / (TWO_PI * cos(delta) * cos(observer.lat) * sin(H))) % 1.0

            # Add the outputs in sorted order, de-duping in the rare case of the same
            # event being found twice on multiple days.
            events = [(midnight + rise, 'rise'),
                      (midnight + transit, 'transit'),
                      (midnight + set_, 'set')]
            events.sort(key = lambda tup: tup[0])
            if (output and output[-1][1] == events[0][1]
                    and abs(output[-1][0] - events[0][0]) < 0.01):
                events.pop(0)
            output.extend(events)
        return output


class Sun(Body):
    """Calucations for the position of the sun."""
    def __init__(self):
        super(Sun, self).__init__(-0.833 * DEG_TO_RAD)

    def geocentric_position(self, dt):
        """Returns the apparent position of the sun at the supplied dynamical time, returning
        a tuple of (spherical coordinates, ecliptic coordinates)."""

        # First calculate the position on the earth in geocentric coordinates
        # pp218 Astronomical Algorithms

        # Time in millenia and centuries
        Tau = (dt - 2451545.0) / 365250.0
        T = Tau * 10.0

        # Accumulate the L, B and R terms using a separate for each term at each order.
        L = B = R = 0.0
        for order, matrix in zip(range(6), (L0, L1, L2, L3, L4, L5)):
            L_component = sum((row[0] * cos(row[1] + row[2]*Tau)) for row in matrix)
            L += L_component * pow(Tau, order) / 1e8
        for order, matrix in zip(range(6), (B0, B1, B2, B3, B4)):
            B_component = sum((row[0] * cos(row[1] + row[2]*Tau)) for row in matrix)
            B += B_component * pow(Tau, order) / 1e8
        for order, matrix in zip(range(6), (R0, R1, R2, R3, R4)):
            R_component = sum((row[0] * cos(row[1] + row[2]*Tau)) for row in matrix)
            R += R_component * pow(Tau, order) / 1e8

        # pp166 for conversion from earth position to sun position
        longitude = (L + pi) % (2 * pi)
        latitude = -B

        # Just for kicks convert to FK5 since we've gone this far, although
        # the correction should not be large enough to be noticed
        lambda_dash = longitude - 1.397 * DEG_TO_RAD * T - 0.00031 * DEG_TO_RAD * T * T
        longitude -= 0.09033/3600.0 * DEG_TO_RAD
        latitude += 0.03916/3600.0 * DEG_TO_RAD * (cos(lambda_dash)-sin(lambda_dash))

        # Now correct for nutation and abberation and convert to equatorial.
        delta_psi, _, epsilon = nutation(dt)
        abberation = -20.4898 / 3600.0 * DEG_TO_RAD / R
        longitude += (delta_psi + abberation)

        ecliptic = SphericalCoordinate(latitude, longitude, range_km=R * ONE_AU_IN_KM)
        return (ecliptic, ecliptic.to_equatorial(epsilon))
 

class Moon(Body):
    """Calucations for the position and phase of the moon."""
    def __init__(self):
        super(Moon, self).__init__(+0.125 * DEG_TO_RAD)

    def geocentric_position(self, dt):
        """Returns the apparent position of the moon at the supplied dynamical time, returning
        a tuple of (spherical coordinates, ecliptic coordinates)."""
        # pp338 Astronomical Algorithms

        # Time in centuries
        T = (dt - 2451545.0)/36525.0
        # Moon's mean longitude.
        Ldash = ((218.3164477 + 481267.88123421 * T - 0.0015786 * T**2 + T**3 / 538841.0
                 - T**4 / 65194000.0) * DEG_TO_RAD) % TWO_PI
        # Mean elongation of the moon.
        D = ((297.8501921 + 445267.1114034 * T - 0.0018819 * T**2 + T**3 / 545868.0
              - T**4 / 113065000.0) * DEG_TO_RAD) % TWO_PI
        # Sun's mean anomaly
        M = ((357.5291092 + 35999.0502909 * T - 0.0001536 * T**2
              + T**3 / 24490000.0) * DEG_TO_RAD) % TWO_PI
        # Moon's mean anomaly
        Mdash = ((134.9633964 + 477198.8675055 * T + 0.0087414 * T**2
                  + T**3 / 69699.0 - T**4 / 14712000.0) * DEG_TO_RAD) % TWO_PI
        # Moon's argument of latitude
        F = ((93.2720950 + 483202.0175233 * T - 0.0036539 * T**2
              - T**3 / 3526000.0 + T**4 / 863310000.0) * DEG_TO_RAD) % TWO_PI
        # Eccentricity of earth's orbit
        E = 1.0 - 0.002516 * T - 0.0000074 * T**2
    
        # Add up coefficients for corrections to longitude and distance
        sigmaL = sigmaR = 0.0
        for arg_LR, coef_LR in zip(arguments_LR, coefficients_LR):
            arg = arg_LR[0] * D + arg_LR[1] * M + arg_LR[2] * Mdash + arg_LR[3] * F
            coef_fac = pow(E, abs(arg_LR[1]))
            sigmaL += coef_fac * coef_LR[0] * sin(arg)
            sigmaR += coef_fac * coef_LR[1] * cos(arg)
    
        # Add up coefficients for corrections to latitude
        sigmaB = 0.0
        for arg_B, coef_B in zip(arguments_B, coefficients_B):
            arg = arg_B[0] * D + arg_B[1] * M + arg_B[2] * Mdash + arg_B[3] * F
            coef_fac = pow(E, abs(arg_B[1]))
            sigmaB += coef_fac * coef_B * sin(arg);
    
        # Now add the corrections due to the planets
        a1 = ((119.75 + 131.849 * T) * DEG_TO_RAD) % TWO_PI
        a2 = ((53.09 + 479264.290 * T) * DEG_TO_RAD) % TWO_PI
        a3 = ((313.45 + 481266.484 * T) * DEG_TO_RAD) % TWO_PI
        sigmaL += 3958.0 * sin(a1) + 1962.0 * sin(Ldash - F) + 318.0 * sin(a2)
        sigmaB += (-2235.0 * sin(Ldash) + 382.0 * sin(a3) + 175.0 * sin(a1 - F)
                   + 175.0 * sin(a1 + F) + 127.0 * sin(Ldash - Mdash) - 115.0 * sin(Ldash + Mdash))
    
        # Get the coordinates in ecliptic.
        latitude = sigmaB / 1000000.0 * DEG_TO_RAD
        longitude = Ldash + sigmaL / 1000000.0 * DEG_TO_RAD
        range_km = 385000.56 + sigmaR / 1000.0

        # Now correct for nutation and convert to equatorial.
        delta_psi, _, epsilon = nutation(dt)
        longitude += delta_psi

        ecliptic = SphericalCoordinate(latitude, longitude, range_km=range_km)
        return (ecliptic, ecliptic.to_equatorial(epsilon))
    

    def phase(self, datetime):
        """Returns moon phase information for the specified timezone aware datetime object as a
        tuple (phase angle in radians, phase description, fraction illuminated)."""
        # pp345 Astronomical Algorithms
        ut = datetime_to_ut(datetime)
        dt = ut_to_dt(ut)

        # Get the moon and sun positions in ecliptic.
        moon, _ = self.geocentric_position(dt)
        sun, _ = Sun().geocentric_position(dt)

        # Calculate the phase angle (aka i) and lit fraction (aka k).
        psi = acos(cos(moon.lat) * cos(moon.lng - sun.lng))
        phase = atan2(sun.rng * sin(psi), moon.rng - sun.rng * cos(psi))
        fraction_illuminated = (1.0 + cos(phase)) / 2.0

        # And name the phase, allowing 30 degrees (a bit over two days) for full/new/quarter.
        phase_deg = phase * RAD_TO_DEG
        if phase_deg < 15.0: desc = 'full'
        elif phase_deg < 75.0: desc = 'waning gibbous'
        elif phase_deg < 105.0: desc = 'last quarter'
        elif phase_deg < 165.0: desc = 'waning crescent'
        elif phase_deg < 195.0: desc = 'new'
        elif phase_deg < 255.0: desc = 'waxing crescent'
        elif phase_deg < 285.0: desc = 'first quarter'
        elif phase_deg < 345.0: desc = 'waxing gibbous'
        else: desc = 'full'

        return (phase, desc, fraction_illuminated)
