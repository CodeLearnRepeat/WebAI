#!/usr/bin/env python3
"""Debug ijson parser events"""

import ijson
import json

# Read the file
file_path = "anotherone.json"
print(f"Testing ijson parsing of: {file_path}")

# First, show the actual content
with open(file_path, 'r') as f:
    content = f.read()
    print(f"\nFile content:\n{content}\n")

# Now parse with ijson and show all events
with open(file_path, 'rb') as f:
    parser = ijson.parse(f)
    
    print("ijson events:")
    print("-" * 60)
    
    event_count = 0
    for prefix, event, value in parser:
        event_count += 1
        # Truncate long values for display
        if isinstance(value, str) and len(value) > 50:
            display_value = value[:50] + "..."
        else:
            display_value = value
            
        print(f"Event {event_count}: prefix='{prefix}', event='{event}', value={repr(display_value)}")
        
        # Stop after 50 events to avoid too much output
        if event_count >= 50:
            print("... (truncated after 50 events)")
            break
    
    print("-" * 60)
    print(f"Total events shown: {event_count}")

# Now test the specific logic from the streaming parser
print("\n\nTesting parsing logic:")
print("-" * 60)

with open(file_path, 'rb') as f:
    parser = ijson.parse(f)
    items = {}
    item_count = 0
    
    for prefix, event, value in parser:
        # Debug the specific conditions
        if event == 'start_array' and prefix == '':
            print(f"Root array started")
        elif event == 'end_array' and prefix == '':
            print(f"Root array ended")
            break
        elif event == 'start_map':
            print(f"Map started with prefix: '{prefix}' (is digit? {prefix.isdigit()})")
            if prefix.isdigit():
                array_index = int(prefix)
                items[array_index] = {}
                print(f"  -> Created item at index {array_index}")
        elif event == 'end_map':
            print(f"Map ended with prefix: '{prefix}' (is digit? {prefix.isdigit()})")
            if prefix.isdigit():
                array_index = int(prefix)
                if array_index in items:
                    print(f"  -> Processing item at index {array_index}: {items[array_index]}")
                    item_count += 1
                    del items[array_index]
        elif '.' in str(prefix):
            parts = str(prefix).split('.', 1)
            if parts[0].isdigit():
                array_index = int(parts[0])
                field_name = parts[1]
                if array_index not in items:
                    items[array_index] = {}
                if event in ('string', 'number', 'boolean', 'null'):
                    items[array_index][field_name] = value
                    print(f"  -> Set {field_name}={repr(value)[:50]} in item {array_index}")

print(f"\nTotal items processed: {item_count}")