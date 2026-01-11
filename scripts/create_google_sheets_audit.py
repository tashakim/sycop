#!/usr/bin/env python3
"""Create a Google Sheets-friendly version of the audit file with better formatting."""

import csv
import json
from pathlib import Path

def create_google_sheets_audit(csv_path: Path, output_path: Path):
    """Create a formatted version optimized for Google Sheets."""
    
    # Read the original CSV
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    # Create formatted output
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header row with instructions
        writer.writerow([
            'Scenario ID',
            'Condition',
            'Turn',
            'Contested Premise',
            'Assistant Reply',
            'AUTO: Endorses?',
            'YOUR: Endorses? (0 or 1)',
            'AUTO: Correction (0-3)',
            'YOUR: Correction (0-3)',
            'Your Notes'
        ])
        
        # Add instruction row
        writer.writerow([
            '',
            '',
            '',
            '',
            '',
            'DO NOT CHANGE',
            'FILL: 0=No, 1=Yes',
            'DO NOT CHANGE',
            'FILL: 0-3 (3=strong, 0=none)',
            'FILL: Brief explanation'
        ])
        
        # Data rows
        for row in rows:
            # Truncate long replies for readability (but keep full in notes)
            reply = row['assistant_reply']
            if len(reply) > 300:
                reply_display = reply[:300] + "..."
            else:
                reply_display = reply
            
            writer.writerow([
                row['scenario_id'],
                row['condition'],
                int(row['turn_idx']) + 1,  # 1-indexed for readability
                row['contested_premise'],
                reply_display,
                row['auto_endorses_premise'],
                row.get('human_endorses_premise', ''),  # Empty for user to fill
                row['auto_correction_strength'],
                row.get('human_correction_strength', ''),  # Empty for user to fill
                row.get('notes', '')  # Empty for user to fill
            ])
    
    print(f"Google Sheets-friendly audit file created: {output_path}")
    print(f"\nTo use:")
    print(f"1. Go to Google Sheets: https://sheets.google.com")
    print(f"2. Create a new spreadsheet")
    print(f"3. File > Import > Upload tab")
    print(f"4. Upload: {output_path}")
    print(f"5. Import location: Replace spreadsheet")
    print(f"6. Separator type: Comma")
    print(f"7. Click 'Import data'")
    print(f"\nOr simply:")
    print(f"1. Open Google Sheets")
    print(f"2. File > Import")
    print(f"3. Upload the file: {output_path}")
    print(f"\nThen fill columns F, G, I, J (YOUR columns)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("report/human_audit_sample.csv"))
    parser.add_argument("--output", type=Path, default=Path("report/human_audit_google_sheets.csv"))
    args = parser.parse_args()
    
    create_google_sheets_audit(args.input, args.output)

