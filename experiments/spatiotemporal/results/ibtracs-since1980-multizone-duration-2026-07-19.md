# IBTrACS multizone duration result

## Workload

- Tracks: 4,775
- Points: 300,033
- Transitions: 295,258
- Transition-zone pairs: 1,476,290
- Instantaneous events: 4,800
- Event/non-event transition-zone pairs: 4,800 / 1,471,490
- Tracks with an instantaneous event: 2,422
- Sustained monitor starts: 14,400
- Sustained events: 12,831
- Unemitted by track end or inverse crossing: 1,569
- Sustained counts: `{'12h:enters': 1212, '12h:leaves': 3123, '24h:enters': 1105, '24h:leaves': 2836, '6h:enters': 1275, '6h:leaves': 3280}`
- Emission lag: `{'emittedAtDeadline': 12778, 'medianSeconds': 0.0, 'p95Seconds': 0.0, 'maximumSeconds': 7800.0}`
- Per-region breakdown: `[{'region': 'EquatorialBand', 'transitionPairs': 295258, 'insidePairs': 25890, 'outsidePairs': 269368, 'eventPairs': 1473, 'nonEventPairs': 293785, 'tracksWithEvents': 1183, 'enters': 233, 'leaves': 1240, 'sustainedEvents': 4107, 'sustainedCounts': {'12h:enters': 183, '12h:leaves': 1191, '24h:enters': 140, '24h:leaves': 1160, '6h:enters': 212, '6h:leaves': 1221}}, {'region': 'NorthernTropics', 'transitionPairs': 295258, 'insidePairs': 151442, 'outsidePairs': 143816, 'eventPairs': 2127, 'nonEventPairs': 293131, 'tracksWithEvents': 1608, 'enters': 843, 'leaves': 1284, 'sustainedEvents': 5847, 'sustainedCounts': {'12h:enters': 802, '12h:leaves': 1177, '24h:enters': 764, '24h:leaves': 1048, '6h:enters': 828, '6h:leaves': 1228}}, {'region': 'NorthAtlanticStudyZone', 'transitionPairs': 295258, 'insidePairs': 36064, 'outsidePairs': 259194, 'eventPairs': 571, 'nonEventPairs': 294687, 'tracksWithEvents': 501, 'enters': 50, 'leaves': 521, 'sustainedEvents': 1491, 'sustainedCounts': {'12h:enters': 44, '12h:leaves': 467, '24h:enters': 36, '24h:leaves': 402, '6h:enters': 48, '6h:leaves': 494}}, {'region': 'WesternPacificStudyZone', 'transitionPairs': 295258, 'insidePairs': 95546, 'outsidePairs': 199712, 'eventPairs': 444, 'nonEventPairs': 294814, 'tracksWithEvents': 390, 'enters': 73, 'leaves': 371, 'sustainedEvents': 907, 'sustainedCounts': {'12h:enters': 67, '12h:leaves': 238, '24h:enters': 57, '24h:leaves': 196, '6h:enters': 70, '6h:leaves': 279}}, {'region': 'SouthIndianStudyZone', 'transitionPairs': 295258, 'insidePairs': 55596, 'outsidePairs': 239662, 'eventPairs': 185, 'nonEventPairs': 295073, 'tracksWithEvents': 140, 'enters': 120, 'leaves': 65, 'sustainedEvents': 479, 'sustainedCounts': {'12h:enters': 116, '12h:leaves': 50, '24h:enters': 108, '24h:leaves': 30, '6h:enters': 117, '6h:leaves': 58}}]`

## Normalized-longitude audit

- Wrapped transitions: 420
- Tracks with wrapped transitions: 366
- Wrapped transitions by basin: `{'EP': 73, 'SP': 176, 'WP': 171}`
- Membership changes on wrapped transitions: `{'EquatorialBand': 2, 'NorthernTropics': 1, 'NorthAtlanticStudyZone': 0, 'WesternPacificStudyZone': 108, 'SouthIndianStudyZone': 0}`
- Latitude-band seam-only changes: 0
- Interpretation: The two latitude-band polygons include both -180 and +180, so their reported changes at wrapped transitions come only from latitude. The WesternPacificStudyZone deliberately ends at 179.999E; its changes are sampled membership changes at that explicit edge. No segment interpolation or antimeridian-crossing polygon is evaluated.

## Exact parity

- All layers match: **True**
- Membership mismatches: 0
- Instantaneous-event mismatches: 0
- Sustained-event mismatches: 0

## Timing

- PULSE median: 25.431120 s
- GEOS/event-sweep median: 10.984675 s

## Claim boundary

Exact discrete sample-and-hold parity for five experiment-defined Point/Polygon zones and 6/12/24-hour sustained events; not continuous trajectory, geodesic, antimeridian-crossing geometry, or full GeoSPARQL conformance.
