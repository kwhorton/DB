"""Map coordinates (latitude, longitude) for every team, keyed by team name.

Teams named for a state or region are placed at its main city (e.g.
Minnesota -> Minneapolis, W. Texas -> Lubbock). Ambiguous names are pinned
to the city noted in the comment beside them.
"""

TEAM_LOCATIONS = {
    # Tier 1 (2033)
    'Atlantic City': (39.3643, -74.4229),
    'Brooklyn': (40.6782, -73.9442),
    'Long Island': (40.7062, -73.6187),      # Hempstead, NY
    'Miami': (25.7617, -80.1918),
    'Raleigh': (35.7796, -78.6382),
    'Rochester': (43.1566, -77.6088),        # Rochester, NY
    'Trenton': (40.2206, -74.7597),
    'Washington': (38.9072, -77.0369),       # Washington, DC
    'Buffalo': (42.8864, -78.8784),
    'Cincinnati': (39.1031, -84.5120),
    'Colo Springs': (38.8339, -104.8214),
    'Columbus': (39.9612, -82.9988),         # Columbus, OH
    'Dayton': (39.7589, -84.1916),
    'Grand Rapids': (42.9634, -85.6681),
    'Minnesota': (44.9778, -93.2650),        # Minneapolis
    'Wichita': (37.6872, -97.3301),
    'Albuquerque': (35.0844, -106.6504),
    'Dallas': (32.7767, -96.7970),
    'Memphis': (35.1495, -90.0490),
    'Mississippi': (32.2988, -90.1848),      # Jackson, MS
    'Oklahoma City': (35.4676, -97.5164),
    'Orlando': (28.5383, -81.3792),
    'San Antonio': (29.4241, -98.4936),
    'Tucson': (32.2226, -110.9747),
    'Bakersfield': (35.3733, -119.0187),
    'Billings': (45.7833, -108.5007),
    'Los Angeles': (34.0522, -118.2437),
    'Phoenix': (33.4484, -112.0740),
    'Portland': (45.5152, -122.6784),        # Portland, OR
    'Sacramento': (38.5816, -121.4944),
    'Seattle': (47.6062, -122.3321),
    'Spokane': (47.6588, -117.4260),

    # Tier 2 (2033)
    'Akron': (41.0814, -81.5190),
    'Annapolis': (38.9784, -76.4922),
    'Huntington': (38.4192, -82.4452),       # Huntington, WV
    'Philadelphia': (39.9526, -75.1652),
    'Portland, ME': (43.6591, -70.2568),
    'Richmond': (37.5407, -77.4360),         # Richmond, VA
    'Toledo': (41.6528, -83.5379),
    'WB Scranton': (41.3270, -75.7863),      # between Wilkes-Barre and Scranton, PA
    'Ann Arbor': (42.2808, -83.7430),
    'Chicago': (41.8781, -87.6298),
    'Des Moines': (41.5868, -93.6250),
    'Ft. Wayne': (41.0793, -85.1394),
    'Green Bay': (44.5133, -88.0133),
    'Indianapolis': (39.7684, -86.1581),
    'Kansas City': (39.0997, -94.5786),      # Kansas City, MO
    'Milwaukee': (43.0389, -87.9065),
    'Atlanta': (33.7490, -84.3880),
    'Baton Rouge': (30.4515, -91.1871),
    'Charlotte': (35.2271, -80.8431),
    'Jacksonville': (30.3322, -81.6557),
    'Montgomery': (32.3792, -86.3077),
    'New Orleans': (29.9511, -90.0715),
    'Tampa Bay': (27.9506, -82.4572),        # Tampa
    'Virginia Beach': (36.8529, -75.9780),
    'Fargo': (46.8772, -96.7898),
    'Hawaii': (21.3069, -157.8583),          # Honolulu
    'Las Vegas': (36.1699, -115.1398),
    'Oakland': (37.8044, -122.2712),
    'Omaha': (41.2565, -95.9345),
    'S. Dakota': (43.5446, -96.7311),        # Sioux Falls
    'Salt Lake City': (40.7608, -111.8910),
    'San Francisco': (37.7749, -122.4194),

    # Tier 3 (2033)
    'Boston': (42.3601, -71.0589),
    'Connecticut': (41.7658, -72.6734),      # Hartford
    'Manchester': (42.9956, -71.4548),       # Manchester, NH
    'New Jersey': (40.7357, -74.1724),       # Newark
    'New York': (40.7831, -73.9712),         # Manhattan
    'Rhode Island': (41.8240, -71.4128),     # Providence
    'Springfield': (42.1015, -72.5898),      # Springfield, MA
    'Syracuse': (43.0481, -76.1474),
    'Cleveland': (41.4993, -81.6944),
    'Madison': (43.0731, -89.4012),          # Madison, WI
    'Morgantown': (39.6295, -79.9559),
    'Pittsburgh': (40.4406, -79.9959),
    'S. Illinois': (37.7273, -89.2168),      # Carbondale
    'St. Louis': (38.6270, -90.1994),
    'Tulsa': (36.1540, -95.9928),
    'West Virginia': (38.3498, -81.6326),    # Charleston, WV
    'Austin': (30.2672, -97.7431),
    'Baltimore': (39.2904, -76.6122),
    'Charleston': (32.7765, -79.9311),       # Charleston, SC
    'Delaware': (39.7391, -75.5398),         # Wilmington
    'Lexington': (38.0406, -84.5037),        # Lexington, KY
    'Louisville': (38.2527, -85.7585),
    'Savannah': (32.0809, -81.0912),
    'Shreveport': (32.5252, -93.7502),
    'Boise': (43.6150, -116.2023),
    'Denver': (39.7392, -104.9903),
    'El Paso': (31.7619, -106.4850),
    'Fresno': (36.7378, -119.7871),
    'Lincoln': (40.8136, -96.7026),          # Lincoln, NE
    'San Jose': (37.3382, -121.8863),
    'Santa Fe': (35.6870, -105.9378),
    'Stockton': (37.9577, -121.2908),

    # Tier 4 (2033)
    'Macon': (32.8407, -83.6324),
    'Montreal': (45.5019, -73.5674),
    'Ottawa': (45.4215, -75.6972),
    'Pensacola': (30.4213, -87.2169),
    'Tallahassee': (30.4383, -84.2807),
    'Toronto': (43.6532, -79.3832),
    'Vermont': (44.4759, -73.2121),          # Burlington
    'Winston-Salem': (36.0999, -80.2442),
    'Cheyenne': (41.1400, -104.8202),
    'Davenport': (41.5236, -90.5776),
    'Detroit': (42.3314, -83.0458),
    'Duluth': (46.7867, -92.1005),
    'Gary': (41.5934, -87.3464),
    'Knoxville': (35.9606, -83.9207),
    'Nashville': (36.1627, -86.7816),
    'Winnipeg': (49.8951, -97.1384),
    'Arlington': (32.7357, -97.1081),        # Arlington, TX
    'Birmingham': (33.5186, -86.8104),       # Birmingham, AL
    'Ft. Worth': (32.7555, -97.3308),
    'Houston': (29.7604, -95.3698),
    'Little Rock': (34.7465, -92.2896),
    'Mesa': (33.4152, -111.8315),            # Mesa, AZ
    'Norman': (35.2226, -97.4395),
    'W. Texas': (33.5779, -101.8552),        # Lubbock
    'Alaska': (61.2181, -149.9003),          # Anchorage
    'Anaheim': (33.8366, -117.9143),
    'Eugene': (44.0521, -123.0868),
    'Long Beach': (33.7701, -118.1937),
    'Reno': (39.5296, -119.8138),
    'San Diego': (32.7157, -117.1611),
    'Tacoma': (47.2529, -122.4443),
    'Vancouver': (49.2827, -123.1207),       # Vancouver, BC
}
