import pandas as pd
import mysql.connector

# Connect to the database
conn = mysql.connector.connect(
    host="matttebbetts.mysql.pythonanywhere-services.com",
    user="matttebbetts",
    password="Test123$",
    database="matttebbetts$crossword"
)

# Create a cursor object
cursor = conn.cursor()

# Execute the query
cursor.execute("SHOW TABLES;")

# Fetch all the results
results = cursor.fetchall()

# Close the cursor and connection
cursor.close()
conn.close()

# Convert the results to a dataframe
df = pd.DataFrame(results, columns=["Tables"])

# Print the dataframe
print(df)
