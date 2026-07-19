# IBTrACS multizone duration result

## Workload

- Tracks: 4,775
- Points: 300,033
- Transitions: 295,258
- Transition-zone pairs: 1,476,290
- Instantaneous events: 4,832
- Event/non-event transition-zone pairs: 4,832 / 1,471,458
- Tracks with an instantaneous event: 2,424
- Sustained monitor starts: 14,496
- Sustained events: 12,870
- Unemitted by track end or inverse crossing: 1,626
- Sustained counts: `{'12h:enters': 1225, '12h:leaves': 3123, '24h:enters': 1116, '24h:leaves': 2836, '6h:enters': 1290, '6h:leaves': 3280}`
- Emission lag: `{'emittedAtDeadline': 12817, 'medianSeconds': 0.0, 'p95Seconds': 0.0, 'maximumSeconds': 7800.0}`
- Per-region breakdown: `[{'region': 'EquatorialBand', 'transitionPairs': 295258, 'insidePairs': 25886, 'outsidePairs': 269372, 'eventPairs': 1482, 'nonEventPairs': 293776, 'tracksWithEvents': 1184, 'enters': 238, 'leaves': 1244, 'sustainedEvents': 4120, 'sustainedCounts': {'12h:enters': 187, '12h:leaves': 1191, '24h:enters': 144, '24h:leaves': 1160, '6h:enters': 217, '6h:leaves': 1221}}, {'region': 'NorthernTropics', 'transitionPairs': 295258, 'insidePairs': 151430, 'outsidePairs': 143828, 'eventPairs': 2150, 'nonEventPairs': 293108, 'tracksWithEvents': 1611, 'enters': 854, 'leaves': 1296, 'sustainedEvents': 5873, 'sustainedCounts': {'12h:enters': 811, '12h:leaves': 1177, '24h:enters': 771, '24h:leaves': 1048, '6h:enters': 838, '6h:leaves': 1228}}, {'region': 'NorthAtlanticStudyZone', 'transitionPairs': 295258, 'insidePairs': 36064, 'outsidePairs': 259194, 'eventPairs': 571, 'nonEventPairs': 294687, 'tracksWithEvents': 501, 'enters': 50, 'leaves': 521, 'sustainedEvents': 1491, 'sustainedCounts': {'12h:enters': 44, '12h:leaves': 467, '24h:enters': 36, '24h:leaves': 402, '6h:enters': 48, '6h:leaves': 494}}, {'region': 'WesternPacificStudyZone', 'transitionPairs': 295258, 'insidePairs': 95546, 'outsidePairs': 199712, 'eventPairs': 444, 'nonEventPairs': 294814, 'tracksWithEvents': 390, 'enters': 73, 'leaves': 371, 'sustainedEvents': 907, 'sustainedCounts': {'12h:enters': 67, '12h:leaves': 238, '24h:enters': 57, '24h:leaves': 196, '6h:enters': 70, '6h:leaves': 279}}, {'region': 'SouthIndianStudyZone', 'transitionPairs': 295258, 'insidePairs': 55596, 'outsidePairs': 239662, 'eventPairs': 185, 'nonEventPairs': 295073, 'tracksWithEvents': 140, 'enters': 120, 'leaves': 65, 'sustainedEvents': 479, 'sustainedCounts': {'12h:enters': 116, '12h:leaves': 50, '24h:enters': 108, '24h:leaves': 30, '6h:enters': 117, '6h:leaves': 58}}]`

## Exact parity

- All layers match: **True**
- Membership mismatches: 0
- Instantaneous-event mismatches: 0
- Sustained-event mismatches: 0

## Timing

- PULSE median: 18.475106 s
- GEOS/event-sweep median: 7.319603 s

## Claim boundary

Exact discrete sample-and-hold parity for five experiment-defined Point/Polygon zones and 6/12/24-hour sustained events; not continuous trajectory, geodesic, or full GeoSPARQL conformance.
