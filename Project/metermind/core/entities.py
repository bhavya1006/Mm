"""The connection hierarchy every later week bills through."""

from config import constants
from metermind.core.exceptions import UnsupportedCategoryError
from metermind.core.tariff_calculations import (
    calculate_bill_amount,
    calculate_slab_energy_charge,
    calculate_units_consumed,
)

_CLASS_BY_CATEGORY = {}


class ServiceConnection:
    def __init__(self, account_number, consumer_category, sanctioned_load_kw, cycle_days,
                 previous_reading, current_reading):
        if consumer_category not in constants.CONSUMER_CATEGORIES:
            raise UnsupportedCategoryError(consumer_category)

        self.account_number = account_number
        self.consumer_category = consumer_category
        self.sanctioned_load_kw = sanctioned_load_kw
        self.cycle_days = cycle_days
        self.previous_reading = previous_reading
        self.current_reading = current_reading

        self.physical_maximum_units = (
            sanctioned_load_kw * constants.HOURS_IN_A_DAY * cycle_days
            * constants.CAPACITY_ALLOWANCE_FACTOR
        )
        self.units_consumed = calculate_units_consumed(
            previous_reading, current_reading, self.physical_maximum_units
        )

    def applicable_slab_table(self):
        return constants.SLAB_TABLE_INR_BY_CATEGORY[self.consumer_category]

    def energy_charge_inr(self):
        return calculate_slab_energy_charge(
            self.consumer_category, self.units_consumed, blocks=self.applicable_slab_table()
        )

    def fixed_charge_inr(self):
        rate = constants.FIXED_CHARGE_INR_PER_KW_BY_CATEGORY[self.consumer_category]
        return self.sanctioned_load_kw * rate

    def electricity_duty_inr(self):
        duty_percent = constants.ELECTRICITY_DUTY_PERCENT_BY_CATEGORY[self.consumer_category]
        return self.energy_charge_inr() * duty_percent / 100

    def subsidy_inr(self):
        qualifying_units = constants.SUBSIDY_QUALIFYING_UNITS_BY_CATEGORY[self.consumer_category]
        rebate_rate = constants.SUBSIDY_INR_PER_UNIT_BY_CATEGORY[self.consumer_category]
        if qualifying_units and self.units_consumed <= qualifying_units:
            return self.units_consumed * rebate_rate
        return 0.0

    def net_bill_inr(self):
        net = (
            self.energy_charge_inr() + self.fixed_charge_inr()
            + self.electricity_duty_inr() - self.subsidy_inr()
        )
        return max(net, 0.0)

    def refusal_reasons(self):
        reasons = []

        would_have_reached_ceiling = (
            self.previous_reading + self.physical_maximum_units >= constants.METER_ROLLOVER_UNITS
        )
        if self.current_reading < self.previous_reading and not would_have_reached_ceiling:
            reasons.append(
                "the current reading is below the previous reading and the meter cannot have "
                "rolled over"
            )

        if self.units_consumed > self.physical_maximum_units:
            reasons.append(
                "the units consumed are above what the sanctioned load could physically draw"
            )

        if not (constants.MINIMUM_CYCLE_DAYS <= self.cycle_days <= constants.MAXIMUM_CYCLE_DAYS):
            reasons.append(
                "the billing cycle length is outside the permitted range"
            )

        return reasons

    def is_billable(self):
        return len(self.refusal_reasons()) == 0


class CommercialConnection(ServiceConnection):
    def energy_charge_inr(self):
        blocks = self.applicable_slab_table()
        units = self.units_consumed
        for upper_limit, rate in blocks:
            if units <= upper_limit:
                return units * rate
        return units * blocks[-1][1]


class AgriculturalConnection(ServiceConnection):
    def fixed_charge_inr(self):
        load_in_horsepower = self.sanctioned_load_kw * constants.HORSEPOWER_PER_KILOWATT
        return load_in_horsepower * constants.FIXED_CHARGE_INR_PER_HORSEPOWER

    def subsidy_inr(self):
        rebate_rate = constants.SUBSIDY_INR_PER_UNIT_BY_CATEGORY[self.consumer_category]
        return self.units_consumed * rebate_rate


_CLASS_BY_CATEGORY = {
    "domestic": ServiceConnection,
    "commercial": CommercialConnection,
    "agricultural": AgriculturalConnection,
}


def create_service_connection(record):
    consumer_category = str(record["consumer_category"]).strip().lower()
    connection_class = _CLASS_BY_CATEGORY.get(consumer_category)
    if connection_class is None:
        raise UnsupportedCategoryError(consumer_category)

    account_number = str(record["account_number"]).strip().upper()

    return connection_class(
        account_number=account_number,
        consumer_category=consumer_category,
        sanctioned_load_kw=float(record["sanctioned_load_kw"]),
        cycle_days=int(float(record["cycle_days"])),
        previous_reading=float(record["previous_reading"]),
        current_reading=float(record["current_reading"]),
    )


if __name__ == "__main__":
    record = {
        "account_number": "ACC10000123",
        "sanctioned_load_kw": 3,
        "cycle_days": 30,
        "previous_reading": 14208,
        "current_reading": 14675,
    }
    for category in ("domestic", "commercial", "agricultural"):
        record["consumer_category"] = category
        connection = create_service_connection(record)
        print(
            f"{category:<13} {connection.units_consumed:.0f} units on a "
            f"{connection.sanctioned_load_kw:.0f} kW connection -> "
            f"Rs. {round(connection.net_bill_inr(), 2)}"
        )

    agricultural = create_service_connection({**record, "consumer_category": "agricultural"})
    rebate_rate = constants.SUBSIDY_INR_PER_UNIT_BY_CATEGORY["agricultural"]
    tariff_rate = agricultural.applicable_slab_table()[0][1]
    print(
        f"an agricultural cycle costs nothing because the rebate of Rs. {rebate_rate} a unit is "
        f"larger than the tariff of Rs. {tariff_rate} a unit, and a bill is never negative"
    )
