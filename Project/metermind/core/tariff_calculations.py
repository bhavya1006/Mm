"""Billing arithmetic every later week prices with."""

import numpy as np
import pandas as pd

from config import constants
from metermind.core.exceptions import UnsupportedCategoryError

TELESCOPIC_CATEGORIES = ("domestic", "agricultural")


def calculate_units_consumed(previous_reading, current_reading, physical_maximum_units):
    if current_reading >= previous_reading:
        return current_reading - previous_reading

    would_have_reached_ceiling = (
        previous_reading + physical_maximum_units >= constants.METER_ROLLOVER_UNITS
    )
    if would_have_reached_ceiling:
        return (constants.METER_ROLLOVER_UNITS - previous_reading) + current_reading

    return 0.0


def calculate_slab_energy_charge(consumer_category, units, blocks=None):
    if consumer_category not in constants.SLAB_TABLE_INR_BY_CATEGORY:
        raise UnsupportedCategoryError(consumer_category)
    if blocks is None:
        blocks = constants.SLAB_TABLE_INR_BY_CATEGORY[consumer_category]

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


def calculate_bill_amount(consumer_category, units, sanctioned_load_kw):
    energy_charge = calculate_slab_energy_charge(consumer_category, units)

    if consumer_category == "agricultural":
        load_in_horsepower = sanctioned_load_kw * constants.HORSEPOWER_PER_KILOWATT
        fixed_charge = load_in_horsepower * constants.FIXED_CHARGE_INR_PER_HORSEPOWER
    else:
        fixed_charge = sanctioned_load_kw * constants.FIXED_CHARGE_INR_PER_KW_BY_CATEGORY[consumer_category]

    duty_percent = constants.ELECTRICITY_DUTY_PERCENT_BY_CATEGORY[consumer_category]
    duty = energy_charge * duty_percent / 100

    qualifying_units = constants.SUBSIDY_QUALIFYING_UNITS_BY_CATEGORY[consumer_category]
    rebate_rate = constants.SUBSIDY_INR_PER_UNIT_BY_CATEGORY[consumer_category]
    rebate = units * rebate_rate if qualifying_units and units <= qualifying_units else 0.0

    return max(energy_charge + fixed_charge + duty - rebate, 0.0)


def calculate_prorated_slab_limits(blocks, day_share):
    prorated = []
    for upper_limit, rate in blocks:
        if upper_limit == constants.UNLIMITED_UNITS:
            prorated.append((upper_limit, rate))
        else:
            prorated.append((upper_limit * day_share, rate))
    return tuple(prorated)


def calculate_prorated_energy_charge(consumer_category, units, cycle_days,
                                      days_on_the_earlier_order, earlier_blocks, later_blocks):
    days_on_the_later_order = cycle_days - days_on_the_earlier_order
    earlier_share = days_on_the_earlier_order / cycle_days
    later_share = days_on_the_later_order / cycle_days

    earlier_units = units * earlier_share
    later_units = units * later_share

    earlier_prorated_blocks = calculate_prorated_slab_limits(earlier_blocks, earlier_share)
    later_prorated_blocks = calculate_prorated_slab_limits(later_blocks, later_share)

    earlier_charge = calculate_slab_energy_charge(
        consumer_category, earlier_units, blocks=earlier_prorated_blocks
    )
    later_charge = calculate_slab_energy_charge(
        consumer_category, later_units, blocks=later_prorated_blocks
    )
    return earlier_charge + later_charge


def _vectorized_energy_charge(consumer_category, units):
    blocks = constants.SLAB_TABLE_INR_BY_CATEGORY[consumer_category]
    units_array = units.to_numpy(dtype=float)

    if consumer_category in TELESCOPIC_CATEGORIES:
        charge = np.zeros_like(units_array)
        lower_limit = 0.0
        for upper_limit, rate in blocks:
            block_span = max(upper_limit - lower_limit, 0.0)
            block_units = np.clip(units_array - lower_limit, 0.0, block_span)
            charge += block_units * rate
            lower_limit = upper_limit
        return pd.Series(charge, index=units.index)

    rate_by_row = np.zeros_like(units_array)
    covered = np.zeros_like(units_array, dtype=bool)
    for upper_limit, rate in blocks:
        newly_covered = (~covered) & (units_array <= upper_limit)
        rate_by_row[newly_covered] = rate
        covered |= newly_covered
    rate_by_row[~covered] = blocks[-1][1]
    return pd.Series(units_array * rate_by_row, index=units.index)


def calculate_bill_amounts(book):
    net_bill_inr = pd.Series(0.0, index=book.index, name="net_bill_inr")

    for consumer_category in constants.CONSUMER_CATEGORIES:
        in_category = book["consumer_category"] == consumer_category
        if not in_category.any():
            continue

        units = book.loc[in_category, "units_consumed"].astype(float)
        sanctioned_load_kw = book.loc[in_category, "sanctioned_load_kw"].astype(float)

        energy_charge = _vectorized_energy_charge(consumer_category, units)

        if consumer_category == "agricultural":
            fixed_charge = (
                sanctioned_load_kw * constants.HORSEPOWER_PER_KILOWATT
                * constants.FIXED_CHARGE_INR_PER_HORSEPOWER
            )
        else:
            fixed_charge = sanctioned_load_kw * constants.FIXED_CHARGE_INR_PER_KW_BY_CATEGORY[consumer_category]

        duty_percent = constants.ELECTRICITY_DUTY_PERCENT_BY_CATEGORY[consumer_category]
        duty = energy_charge * duty_percent / 100

        qualifying_units = constants.SUBSIDY_QUALIFYING_UNITS_BY_CATEGORY[consumer_category]
        rebate_rate = constants.SUBSIDY_INR_PER_UNIT_BY_CATEGORY[consumer_category]
        if qualifying_units:
            qualifies = units <= qualifying_units
        else:
            qualifies = pd.Series(False, index=units.index)
        rebate = units.where(qualifies, 0.0) * rebate_rate

        net = (energy_charge + fixed_charge + duty - rebate).clip(lower=0.0)
        net_bill_inr.loc[in_category] = net

    return net_bill_inr


if __name__ == "__main__":
    units = calculate_units_consumed(14208, 14675, 5000)
    print("units consumed:", units)
    charge = calculate_slab_energy_charge("domestic", units)
    print("energy charge :", round(charge, 1))
    demand = calculate_bill_amount("domestic", units, 3)
    print("current demand:", round(demand, 2))

    blocks = constants.SLAB_TABLE_INR_BY_CATEGORY["domestic"]
    split = calculate_prorated_energy_charge("domestic", units, 30, 14, blocks, blocks)
    print(f"a cycle split 14 days on the old order and 16 on the new: {round(split, 2)}")
