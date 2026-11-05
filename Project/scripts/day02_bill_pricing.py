"""Same pricing as Day 1, expressed as functions and a class, covering all three categories."""

UNLIMITED_UNITS = float("inf")

# !!! VERIFY the domestic block-3 rate (6.500735) against your real constants.py - see chat.
SLAB_RATES_INR = {
    "domestic": ((100.0, 3.50), (200.0, 4.90), (500.0, 6.500735), (UNLIMITED_UNITS, 7.16)),
    "commercial": ((200.0, 7.50), (UNLIMITED_UNITS, 8.60)),
    "agricultural": ((UNLIMITED_UNITS, 4.50),),
}

TELESCOPIC_CATEGORIES = ("domestic",)

FIXED_CHARGE_PER_KW_INR = {"domestic": 50.0, "commercial": 75.0}
FIXED_CHARGE_PER_HORSEPOWER_INR = 100.0
HORSEPOWER_PER_KILOWATT = 1.0 / 0.746

ELECTRICITY_DUTY_PERCENT = {"domestic": 5.0, "commercial": 7.0, "agricultural": 0.0}

REBATE_PER_UNIT_INR = {"domestic": 1.50, "commercial": 0.0, "agricultural": 5.00}
REBATE_QUALIFYING_UNITS = {"domestic": 100.0, "commercial": 0.0, "agricultural": 3000.0}

METER_CEILING_UNITS = 100000.0


def units_consumed(previous_reading, current_reading, physical_maximum_units):
    if current_reading >= previous_reading:
        return current_reading - previous_reading

    would_have_reached_ceiling = previous_reading + physical_maximum_units >= METER_CEILING_UNITS
    if would_have_reached_ceiling:
        return (METER_CEILING_UNITS - previous_reading) + current_reading

    return 0.0


def slab_energy_charge(consumer_category, units):
    blocks = SLAB_RATES_INR[consumer_category]

    if consumer_category in TELESCOPIC_CATEGORIES:
        charge = 0.0
        lower_limit = 0.0
        for upper_limit, rate in blocks:
            block_units = min(max(units - lower_limit, 0.0), max(upper_limit - lower_limit, 0.0))
            charge += block_units * rate
            lower_limit = upper_limit
        return charge

    for upper_limit, rate in blocks:
        if units <= upper_limit:
            return units * rate
    return units * blocks[-1][1]


def apply_fixed_charge(consumer_category, sanctioned_load_kw):
    if consumer_category == "agricultural":
        load_in_horsepower = sanctioned_load_kw * HORSEPOWER_PER_KILOWATT
        return load_in_horsepower * FIXED_CHARGE_PER_HORSEPOWER_INR
    return sanctioned_load_kw * FIXED_CHARGE_PER_KW_INR[consumer_category]


def apply_electricity_duty(consumer_category, energy_charge_inr):
    return energy_charge_inr * ELECTRICITY_DUTY_PERCENT[consumer_category] / 100


def apply_subsidy(consumer_category, units):
    qualifying_units = REBATE_QUALIFYING_UNITS[consumer_category]
    rebate_rate = REBATE_PER_UNIT_INR[consumer_category]
    if qualifying_units and units <= qualifying_units:
        return units * rebate_rate
    return 0.0


def net_bill_amount(consumer_category, units, sanctioned_load_kw):
    energy_charge_inr = slab_energy_charge(consumer_category, units)
    fixed_charge_inr = apply_fixed_charge(consumer_category, sanctioned_load_kw)
    duty_inr = apply_electricity_duty(consumer_category, energy_charge_inr)
    rebate_inr = apply_subsidy(consumer_category, units)
    net = energy_charge_inr + fixed_charge_inr + duty_inr - rebate_inr
    return max(net, 0.0)


class MeterReading:
    def __init__(self, account_number, consumer_category, sanctioned_load_kw, cycle_days,
                 previous_reading, current_reading):
        self.account_number = account_number
        self.consumer_category = consumer_category
        self.sanctioned_load_kw = sanctioned_load_kw
        self.cycle_days = cycle_days
        self.previous_reading = previous_reading
        self.current_reading = current_reading

    def price(self):
        physical_maximum_units = self.sanctioned_load_kw * 24 * self.cycle_days * 1.10
        units = units_consumed(self.previous_reading, self.current_reading,
                               physical_maximum_units)
        net_inr = net_bill_amount(self.consumer_category, units, self.sanctioned_load_kw)
        return units, net_inr


if __name__ == "__main__":
    account_number = input().strip().upper()
    consumer_category = input().strip().lower()
    sanctioned_load_kw = float(input())
    cycle_days = int(input())
    previous_reading = float(input())
    current_reading = float(input())
    arrears_inr = float(input())
    late_payment_surcharge_percent = float(input())

    reading = MeterReading(account_number, consumer_category, sanctioned_load_kw, cycle_days,
                           previous_reading, current_reading)
    units, current_demand_inr = reading.price()
    late_payment_surcharge_inr = arrears_inr * late_payment_surcharge_percent / 100
    amount_payable_inr = current_demand_inr + arrears_inr + late_payment_surcharge_inr

    print(f"Account number: {account_number}")
    print(f"Consumer category: {consumer_category}")
    print(f"Units consumed: {round(units, 1)}")
    print(f"Energy charge: {round(slab_energy_charge(consumer_category, units), 2)}")
    print(f"Fixed charge: {round(apply_fixed_charge(consumer_category, sanctioned_load_kw), 2)}")
    print(f"Current demand: {round(current_demand_inr, 2)}")
    print(f"Amount payable: {round(amount_payable_inr, 2)}")
