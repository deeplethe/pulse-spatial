# IBTrACS multizone duration result

## Workload

- Tracks: 223
- Points: 13,784
- Transitions: 13,561
- Transition-zone pairs: 67,805
- Instantaneous events: 175
- Event/non-event transition-zone pairs: 175 / 67,630
- Tracks with an instantaneous event: 96
- Sustained monitor starts: 525
- Sustained events: 475
- Unemitted by track end or inverse crossing: 50
- Sustained counts: `{'12h:enters': 34, '12h:leaves': 127, '24h:enters': 31, '24h:leaves': 116, '6h:enters': 35, '6h:leaves': 132}`
- Emission lag: `{'emittedAtDeadline': 472, 'medianSeconds': 0.0, 'p95Seconds': 0.0, 'maximumSeconds': 3600.0}`
- Per-region breakdown: `[{'region': 'EquatorialBand', 'transitionPairs': 13561, 'insidePairs': 768, 'outsidePairs': 12793, 'eventPairs': 38, 'nonEventPairs': 13523, 'tracksWithEvents': 31, 'enters': 6, 'leaves': 32, 'sustainedEvents': 110, 'sustainedCounts': {'12h:enters': 6, '12h:leaves': 31, '24h:enters': 4, '24h:leaves': 31, '6h:enters': 6, '6h:leaves': 32}}, {'region': 'NorthernTropics', 'transitionPairs': 13561, 'insidePairs': 7768, 'outsidePairs': 5793, 'eventPairs': 78, 'nonEventPairs': 13483, 'tracksWithEvents': 66, 'enters': 22, 'leaves': 56, 'sustainedEvents': 217, 'sustainedCounts': {'12h:enters': 21, '12h:leaves': 52, '24h:enters': 20, '24h:leaves': 49, '6h:enters': 22, '6h:leaves': 53}}, {'region': 'NorthAtlanticStudyZone', 'transitionPairs': 13561, 'insidePairs': 2623, 'outsidePairs': 10938, 'eventPairs': 38, 'nonEventPairs': 13523, 'tracksWithEvents': 33, 'enters': 3, 'leaves': 35, 'sustainedEvents': 100, 'sustainedCounts': {'12h:enters': 3, '12h:leaves': 31, '24h:enters': 3, '24h:leaves': 27, '6h:enters': 3, '6h:leaves': 33}}, {'region': 'WesternPacificStudyZone', 'transitionPairs': 13561, 'insidePairs': 3383, 'outsidePairs': 10178, 'eventPairs': 14, 'nonEventPairs': 13547, 'tracksWithEvents': 13, 'enters': 1, 'leaves': 13, 'sustainedEvents': 28, 'sustainedCounts': {'12h:enters': 1, '12h:leaves': 9, '24h:enters': 1, '24h:leaves': 6, '6h:enters': 1, '6h:leaves': 10}}, {'region': 'SouthIndianStudyZone', 'transitionPairs': 13561, 'insidePairs': 2153, 'outsidePairs': 11408, 'eventPairs': 7, 'nonEventPairs': 13554, 'tracksWithEvents': 5, 'enters': 3, 'leaves': 4, 'sustainedEvents': 20, 'sustainedCounts': {'12h:enters': 3, '12h:leaves': 4, '24h:enters': 3, '24h:leaves': 3, '6h:enters': 3, '6h:leaves': 4}}]`

## Normalized-longitude audit

- Wrapped transitions: 20
- Tracks with wrapped transitions: 16
- Wrapped transitions by basin: `{'EP': 2, 'SP': 6, 'WP': 12}`
- Membership changes on wrapped transitions: `{'EquatorialBand': 0, 'NorthernTropics': 0, 'NorthAtlanticStudyZone': 0, 'WesternPacificStudyZone': 5, 'SouthIndianStudyZone': 0}`
- Latitude-band seam-only changes: 0
- Interpretation: The two latitude-band polygons include both -180 and +180, so their reported changes at wrapped transitions come only from latitude. The WesternPacificStudyZone deliberately ends at 179.999E; its changes are sampled membership changes at that explicit edge. No segment interpolation or antimeridian-crossing polygon is evaluated.

## Exact parity

- All layers match: **True**
- Membership mismatches: 0
- Instantaneous-event mismatches: 0
- Sustained-event mismatches: 0

## Timing

- PULSE median: 0.854944 s
- GEOS/event-sweep median: 0.458376 s

## Claim boundary

Exact discrete sample-and-hold parity for five experiment-defined Point/Polygon zones and 6/12/24-hour sustained events; not continuous trajectory, geodesic, antimeridian-crossing geometry, or full GeoSPARQL conformance.
