
import asyncio
import aiomysql
import pandas as pd
from config import db_config
from bot_functions import bot_print

# sql to df
async def get_df_from_sql(query, params=None):   

    # set parameters
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        try:
            # Connect to the database
            conn = await aiomysql.connect(**db_config, loop=asyncio.get_running_loop())

            # Create a cursor and execute the query
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                bot_print("Query to execute:", query)
                bot_print("Parameters to use:", params)

                await cursor.execute(query, params)
                result = await cursor.fetchall()

            # Close the connection
            await conn.close()

            # Convert the result to a pandas DataFrame
            return pd.DataFrame(result) if result else pd.DataFrame()

        except asyncio.TimeoutError:
            bot_print("SQL Timeout Error")
            attempts += 1
            if attempts >= max_attempts:
                # Return an empty DataFrame after max attempts
                bot_print("Max attempts reached")
                return pd.DataFrame()

            await asyncio.sleep(1)  # Wait for a bit before retrying (1 second in this case)

        except Exception as e:
            # For other exceptions, you might want to handle them differently or log them
            bot_print(f"Error in bot_sql.py line 46: {e}")
            return pd.DataFrame()

    # Return an empty DataFrame if all attempts fail
    return pd.DataFrame()

# df to sql
async def send_df_to_sql(df, table_name, if_exists='append'):

    # Convert DataFrame to tuples
    data_tuples = [tuple(x) for x in df.to_numpy()]

    # Construct SQL query for inserting data
    cols = ', '.join(df.columns)
    placeholders = ', '.join(['%s'] * len(df.columns))
    insert_query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

    # Handle the 'if_exists' cases
    if if_exists == 'replace':
        delete_query = f"DELETE FROM {table_name}"
    elif if_exists == 'fail':
        check_query = f"SELECT 1 FROM {table_name} LIMIT 1"

    # Connect and execute
    async with aiomysql.create_pool(**db_config, loop=asyncio.get_running_loop()) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:

                # If 'replace', delete existing data
                if if_exists == 'replace':
                    await cur.execute(delete_query)

                # If 'fail', check if the table is empty
                elif if_exists == 'fail':
                    await cur.execute(check_query)
                    if await cur.fetchone():
                        raise ValueError(f"Table {table_name} is not empty. Aborting operation.")

                # Execute the insert query
                await cur.executemany(insert_query, data_tuples)
                await conn.commit()
