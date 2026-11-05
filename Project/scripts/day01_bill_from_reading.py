account_number = input().strip().upper()
sanctioned_load_kw = float(input())
cycle_days = int(input())
previous_reading = float(input())
current_reading = float(input())
arrears_inr = float(input())
late_payment_surcharge_percent = float(input())

# The domestic schedule, held by hand. From Week 1 Day 3 onward this is read from
# config/constants.py instead.
# !!! VERIFY THIS ONE RATE against your real constants.py - see the chat for why.
DOMESTIC_SLAB_TABLE = (
    (100.0, 3.50),
    (200.0, 4.90),
    (500.0, 6.500735),
    (float("inf"), 7.16),
)
FIXED_CHARGE_PER_KW_INR = 50.0
ELECTRICITY_DUTY_PERCENT = 5.0
REBATE_PER_UNIT_INR = 1.50
REBATE_QUALIFYING_UNITS = 100.0
METER_CEILING_UNITS = 100000.0
HOURS_IN_A_DAY = 24
CAPACITY_ALLOWANCE_FACTOR = 1.10
MINIMUM_CYCLE_DAYS = 7
MAXIMUM_CYCLE_DAYS = 90

physical_maximum_units = (
    sanctioned_load_kw * HOURS_IN_A_DAY * cycle_days * CAPACITY_ALLOWANCE_FACTOR
)

meter_went_backwards = False
if current_reading >= previous_reading:
    units_consumed = current_reading - previous_reading
else:
    would_have_reached_ceiling = previous_reading + physical_maximum_units >= METER_CEILING_UNITS
    if would_have_reached_ceiling:
        units_consumed = (METER_CEILING_UNITS - previous_reading) + current_reading
    else:
        units_consumed = 0.0
        meter_went_backwards = True

energy_charge_inr = 0.0
lower_limit = 0.0
for upper_limit, rate in DOMESTIC_SLAB_TABLE:
    block_units = min(max(units_consumed - lower_limit, 0.0), max(upper_limit - lower_limit, 0.0))
    energy_charge_inr += block_units * rate
    lower_limit = upper_limit

fixed_charge_inr = sanctioned_load_kw * FIXED_CHARGE_PER_KW_INR
electricity_duty_inr = energy_charge_inr * ELECTRICITY_DUTY_PERCENT / 100
if units_consumed <= REBATE_QUALIFYING_UNITS:
    rebate_inr = units_consumed * REBATE_PER_UNIT_INR
else:
    rebate_inr = 0.0

current_demand_inr = energy_charge_inr + fixed_charge_inr + electricity_duty_inr - rebate_inr
if current_demand_inr < 0.0:
    current_demand_inr = 0.0

late_payment_surcharge_inr = arrears_inr * late_payment_surcharge_percent / 100
amount_payable_inr = current_demand_inr + arrears_inr + late_payment_surcharge_inr

rejections = []
if meter_went_backwards:
    rejections.append(
        "Rejected: the current reading is below the previous reading and the meter "
        "cannot have rolled over"
    )
if units_consumed > physical_maximum_units:
    rejections.append(
        f"Rejected: the units consumed are above what a {sanctioned_load_kw} kW connection "
        f"could physically draw across a {cycle_days} day cycle"
    )
if not (MINIMUM_CYCLE_DAYS <= cycle_days <= MAXIMUM_CYCLE_DAYS):
    rejections.append(
        f"Rejected: the billing cycle length of {cycle_days} days is outside the permitted "
        f"range of {MINIMUM_CYCLE_DAYS} to {MAXIMUM_CYCLE_DAYS} days"
    )

print(f"Account number: {account_number}")
print(f"Units consumed: {round(units_consumed, 1)}")
print(f"Energy charge: {round(energy_charge_inr, 2)}")
print(f"Fixed charge: {round(fixed_charge_inr, 2)}")
print(f"Electricity duty: {round(electricity_duty_inr, 2)}")
print(f"Rebate: {round(rebate_inr, 2)}")
print(f"Current demand: {round(current_demand_inr, 2)}")
print(f"Late payment surcharge: {round(late_payment_surcharge_inr, 2)}")
print(f"Amount payable: {round(amount_payable_inr, 2)}")

for rejection in rejections:
    print(rejection)

if rejections:
    print(f"Reading is not billable: {len(rejections)} reason(s) found")
else:
    print("Reading is billable")
