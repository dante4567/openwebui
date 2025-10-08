
import sqlite3
import json
import time

# Read the JSON content from the file
with open('/tmp/config.json', 'r') as f:
    json_content = f.read()

# Connect to the database
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()

# Get the current time
now = int(time.time())

# Get the version from the json_content
version = json.loads(json_content).get('version', 0)

# Insert the data
cursor.execute("INSERT INTO config (id, data, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
               (1, json_content, version, now, now))

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Config data inserted successfully.")
