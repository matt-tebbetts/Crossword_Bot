from sqlalchemy import create_engine
import sshtunnel
import pandas as pd
import mysql.connector

# set timeouts
sshtunnel.SSH_TIMEOUT = 5.0
sshtunnel.TUNNEL_TIMEOUT = 5.0

# port
port_nbr = 3306

# create ssh tunnel
with sshtunnel.SSHTunnelForwarder(
        'ssh.pythonanywhere.com',
        ssh_username='matttebbetts',
        ssh_password='SD7e79+VBAv8#f%',
        remote_bind_address=('matttebbetts.mysql.pythonanywhere-services.com', port_nbr)
) as tunnel:

    print('trying connection via create_engine...')
    # create engine
    db_user = 'matttebbetts'
    db_pass = 'Test123!'
    db_host = '127.0.0.1'
    db_port = tunnel.local_bind_port
    db_name = 'matttebbetts$crossword'
    db_string = f"{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    print(f"string is: " + db_string)
    print('trying to create engine now...')
    engine = create_engine(f"mysql+mysqldb://+{db_string}")
    print('got here')

    # send data to sql
    users_csv = 'files/users.csv'
    users_df = pd.read_csv(users_csv)
    users_df.to_sql(name='users',
                    con=engine,
                    if_exists='append',
                    index=False)
    print('sent the dataframe')