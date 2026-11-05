# `scripts`

These are standalone learning/demo programs that read values from standard input rather than using FastAPI.

- `day01_bill_from_reading.py`: one-file domestic billing calculator. It handles reading differences and rollover, domestic slabs, fixed charge, duty, rebate, arrears, surcharge, and rejection messages.
- `day02_bill_pricing.py`: refactors similar pricing into functions and `MeterReading`, and adds domestic, commercial, and agricultural categories. It prints a shorter summary and has less validation/reporting than the API domain layer.

Both scripts contain tariff constants locally. The production-style billing path is under `metermind/core/`, where tariff values are read from the external `config.constants` module.
