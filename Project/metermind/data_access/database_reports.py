"""Three grouped reports over the readings table, done in SQL."""

from pathlib import Path

from config import constants
from metermind.data_access.database_loader import READINGS_TABLE

EXCEPTION_RATE_QUERY = f"""
    SELECT consumer_category,
           COUNT(*) AS readings,
           1.0 * SUM(CASE WHEN exception_class != 'genuine_high_usage' THEN 1 ELSE 0 END)
               / COUNT(*) AS exception_rate
    FROM {READINGS_TABLE}
    GROUP BY consumer_category
    ORDER BY exception_rate DESC
"""

ESTIMATED_READ_QUERY = f"""
    SELECT billing_period,
           COUNT(*) AS readings,
           1.0 * SUM(CASE WHEN read_type = 'estimated' THEN 1 ELSE 0 END)
               / COUNT(*) AS estimated_read_share
    FROM {READINGS_TABLE}
    GROUP BY billing_period
    ORDER BY billing_period
"""

BILLED_UNITS_QUERY = f"""
    SELECT division,
           COUNT(*) AS readings,
           SUM(CAST(units_consumed AS REAL)) AS units_billed
    FROM {READINGS_TABLE}
    GROUP BY division
    ORDER BY units_billed DESC
"""


def _run(database, query):
    cursor = database.connection.execute(query)
    return [dict(row) for row in cursor.fetchall()]


def exception_rate_by_category(database):
    return _run(database, EXCEPTION_RATE_QUERY)


def estimated_read_share_by_month(database):
    return _run(database, ESTIMATED_READ_QUERY)


def billed_units_by_division(database):
    return _run(database, BILLED_UNITS_QUERY)


def write_report_files(database, report_path):
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    sections = (
        ("EXCEPTION RATE BY CATEGORY", exception_rate_by_category(database)),
        ("ESTIMATED READ SHARE BY MONTH", estimated_read_share_by_month(database)),
        ("BILLED UNITS BY DIVISION", billed_units_by_division(database)),
    )

    with open(report_path, "w", encoding="utf-8") as handle:
        for heading, rows in sections:
            handle.write(heading + "\n")
            if rows:
                columns = list(rows[0].keys())
                handle.write(",".join(columns) + "\n")
                for row in rows:
                    handle.write(",".join(str(row[column]) for column in columns) + "\n")
            handle.write("\n")

    return report_path


if __name__ == "__main__":
    from metermind.data_access.database_loader import ReadingDatabase

    database = ReadingDatabase(constants.READINGS_DATABASE_PATH)
    written = write_report_files(database, constants.READING_REPORTS_PATH)
    print(f"written: {written}")
