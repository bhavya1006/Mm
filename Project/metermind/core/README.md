# `metermind.core`

The core package contains framework-independent billing behavior and reusable validation.

- `__init__.py`: package marker.
- `decorators.py`: provides `reject_negative_readings`, which rejects negative numeric arguments, and `measure_execution_duration`, which records the last call duration on the wrapper.
- `entities.py`: defines `ServiceConnection`, `CommercialConnection`, and `AgriculturalConnection`; selects the category class, calculates physical capacity and consumption, computes charges, and reports refusal reasons.
- `exceptions.py`: domain exception types such as unsupported category, invalid reading, and storage errors.
- `tariff_calculations.py`: scalar and vectorized consumption/slab/bill calculations, including prorated tariff-order calculations.
- `validators.py`: format checks for account numbers, meter serials, billing periods, and email addresses.

The API calls `create_service_connection` and then builds `ReadingReply` from the returned domain object. This is the main billing source used by live reading endpoints.
