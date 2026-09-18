"""
Use this script to pull PI AF Category data and convert it to CSV format.
Additional changes will need to be made to align the columns with the MTL.
"""
import xml.etree.ElementTree as ET
import csv
import sys


def strip_namespace(tag):
    """Remove XML namespace from tag name if present."""
    return tag.split("}", 1)[-1]


def xml_to_csv(input_file, output_file, record_tag=None):
    tree = ET.parse(input_file)
    root = tree.getroot()

    if record_tag:
        records = root.findall(record_tag)
    else:
        records = list(root)

    rows = []
    columns = []

    for record in records:
        row = {}

        for child in record:
            column_name = strip_namespace(child.tag)
            row[column_name] = (child.text or "").strip()

            if column_name not in columns:
                columns.append(column_name)

        rows.append(row)

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Converted {len(rows)} records to {output_file}")
    print(f"Columns: {', '.join(columns)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python xml_to_csv.py input.xml output.csv [record_tag]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    record_tag = sys.argv[3] if len(sys.argv) > 3 else None

    xml_to_csv(input_file, output_file, record_tag)
