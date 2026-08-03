"""
AI version of this in a tk app.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import xml.etree.ElementTree as ET
import csv


def strip_namespace(tag):
    return tag.split("}", 1)[-1]


def xml_text_to_rows(xml_text):
    root = ET.fromstring(xml_text)

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

    return rows, columns


def convert_to_csv():
    xml_text = xml_input.get("1.0", "end-1c").strip()

    if not xml_text:
        messagebox.showwarning("No XML", "Please paste XML into the text box first.")
        return

    try:
        rows, columns = xml_text_to_rows(xml_text)
    except ET.ParseError as e:
        messagebox.showerror("XML Parse Error", f"The XML could not be parsed:\n\n{e}")
        return

    if not rows:
        messagebox.showwarning("No Records", "No records were found in the XML.")
        return

    output_file = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not output_file:
        return

    try:
        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

        messagebox.showinfo(
            "Success",
            f"Converted {len(rows)} records to CSV successfully."
        )

    except Exception as e:
        messagebox.showerror("Save Error", f"Could not save CSV:\n\n{e}")


root = tk.Tk()
root.title("XML to CSV Converter")
root.geometry("900x600")

label = tk.Label(root, text="Paste XML below:")
label.pack(anchor="w", padx=10, pady=(10, 0))

xml_input = ScrolledText(root, wrap=tk.WORD, height=25)
xml_input.pack(fill="both", expand=True, padx=10, pady=10)

button = tk.Button(root, text="Convert to CSV", command=convert_to_csv)
button.pack(pady=(0, 10))

root.mainloop()