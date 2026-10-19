# Test company: Plantaris Health AG (fictional)

Fictional company for end-to-end tests of the business-model flow (paste text, need card, leads). Any resemblance to a real company is unintended. Paste the section "Business model" into the workspace as is.

## Business model

Plantaris Health AG is a Zurich-based start-up (seed stage, 6 employees) developing **Plantaris Step**, a smart shoe insole for people with diabetes. Up to a quarter of people with diabetes develop a foot ulcer during their lifetime, and many of these ulcers start from repeated high pressure on parts of the sole that the patient no longer feels because of peripheral neuropathy.

The insole contains 16 thin-film pressure sensors, a temperature sensor array and an inertial measurement unit. It streams data to a smartphone app over Bluetooth. Our algorithm detects sustained high plantar pressure and local temperature rises, which precede ulceration, and warns the patient to offload the foot. Gait data (step count, stride variability, balance) are summarised weekly for the treating diabetologist or podiatrist.

We have a working prototype tested on 12 healthy volunteers. To move forward we need:

- validation of our plantar pressure and gait measurements against a reference gait laboratory, with experts in foot biomechanics;
- clinical partners in diabetology and diabetic foot care to design and run a pilot study with 60 patients with neuropathy;
- support with machine learning on wearable sensor data, including fall-risk estimation from gait in older patients;
- guidance on the regulatory route as a Class IIa medical device under Swiss MedDO / EU MDR, and help setting up the clinical investigation (ethics submission, monitoring);
- a possible location in the Bern region close to a university hospital, with access to translational medicine and entrepreneurship programmes.

Business model: the insole is sold to diabetes clinics and podiatry practices (hardware plus annual software licence per patient); in a second step we seek reimbursement by Swiss health insurers.

## Expected needs (need card)

Roughly these five; wording from Apertus 8B will vary.

1. Foot biomechanics, plantar pressure and gait analysis
2. Diabetic foot, diabetology, clinical pilot study
3. Machine learning on wearable sensor data, fall risk, older adults
4. Medical device regulation (MedDO / MDR), clinical investigation, ethics, monitoring
5. Translational medicine, start-up support, Bern location

## Expected leads (top 10)

Checked against `live_medtech` on 2026-10-19. A lead counts as found if its unit appears in the top 10.

| Need | Unit id | Unit | Contact persons in the index |
| --- | --- | --- | --- |
| 1 | `bfh-foot-biomechanics-and-technology` | BFH Foot Biomechanics and Technology | Patric Eichelberger (Bern Movement Lab), Heiner Baur |
| 1 | `orthopaedie` | Department of Orthopaedic Surgery and Traumatology, Inselspital | |
| 2 | `udem` | UDEM, Inselspital | |
| 2 | `dcberne-non-invasive-methods` | DCB Focus Area Non-invasive methods | |
| 3 | `artorg-ger` | ARTORG Gerontechnology and Rehabilitation | Tobias Nef, René Müri, Urs Mosimann |
| 4 | `dcr-clinical-study-management--regulatory-affairs` | DCR Clinical Study Management & Regulatory Affairs | |
| 4 | `swissmedic` | Swissmedic: medical devices | |
| 4 | `dcr-monitoring` | DCR Monitoring | |
| 5 | `sitem` | sitem-insel School | |

Pass: at least 7 of 9 units in the top 10, and every need card line has at least one lead (no gap in the coverage line).

Acceptable extras: `bfh-rehabilitation-technology`, `bfh-spinal-movement-biomechanics`, `dcberne-sensing-smart-monitoring`, `dcr-consulting`, `sitem-insel`, `artorg-mln`.

Signs of a problem: leads from forensic, veterinary or physics units (e.g. `irm-forensic-physics-and-ballistics` matches "wound"); an explanation naming a person not on the quoted page.
