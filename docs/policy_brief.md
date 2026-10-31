# EpiScope: a cautious planning aid

**To:** Director, Disease Control & Preparedness Unit  
**Purpose:** Demonstrate how district surveillance, case projections and supply planning could be brought together.

## What the prototype shows

The dashboard puts weekly district reports, unusual-rise flags, short-term planning estimates, illustrative stocks and a preparedness calendar in one place. It is a classroom demonstration: disease encounters, facilities, stock and injected outbreaks are synthetic. Optional reference inputs include geoBoundaries district shapes, WorldPop modelled 2022 population estimates, and Open-Meteo historical weather. These inputs do not turn the synthetic encounter series into current disease surveillance. The dashboard does not describe current disease burden in Bangladesh and should not guide actual treatment or supply decisions.

## Three recommendations for a real pilot

1. **Start with a limited, audited district pilot.** Agree on one case definition and reporting timetable with facilities and laboratories. Track missing reports, revisions and reporting delays alongside counts. Expected impact: fewer false alarms caused by late backfills and clearer responsibility for follow-up.
2. **Use warnings to prompt review, not automatic action.** Ask surveillance staff to verify a signal against facility completeness, laboratory confirmation, weather and local context. Expected impact: earlier investigation while reducing the chance that reporting changes are mistaken for an outbreak.
3. **Protect fairness and privacy in supply planning.** Publish the inputs and reasons behind each recommendation, reserve a minimum share for every district, then direct remaining stock toward forecast need and vulnerability. Expected impact: transparent trade-offs and less risk of leaving low-volume districts without a basic allocation.

## How to read the dashboard

Choose a disease and district to coordinate the views. With public data enabled, the district view uses public ADM2 boundaries and population denominators; otherwise it shows schematic tiles. The time series separates previous reports from the planning estimate and shows an uncertainty range. The heat view shows seasonal patterns. The supply table compares an illustrative demand estimate with stock and a suggested amount. The warning list highlights unusual rises that need human review. Counts from one to four are hidden; “suppressed” values must not be inferred from totals.

## Confidence and limits

Case encounters, facilities, stocks and outbreak injections are synthetic. Population denominators are synthetic unless public-data mode has been run; that mode uses modelled WorldPop estimates, not official BBS census counts. Public weather and boundary acquisition is opt-in; check source_metadata.json before interpreting those views. The current detector and forecast are transparent baselines, not validated forecasts. No measured sensitivity, false-alert rate, forecast error, cost-effectiveness or user-study result is claimed. Reporting delays, service disruptions and revisions need validation against real operational data before any pilot recommendation.

## Data protection

The generator uses fictional IDs. The pipeline hashes IDs before silver using a secret supplied outside the repository, removes direct IDs, and exports district-week totals only. This prototype contains no real patient records. Any real pilot would need a lawful purpose, access controls, retention limits, secure key management, audit logs and privacy review. Public releases need additional protection against identifying people through linked or complementary totals.


