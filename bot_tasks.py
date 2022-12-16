import bot_functions
import pytz
from datetime import datetime
from sys import exit

now = datetime.now(pytz.timezone('US/Eastern'))
now_ts = now.strftime("%Y-%m-%d %H:%M:%S")
print(now_ts)

# set hours
run_hours = [16, 17, 20, 21, 23]

if now.hour not in run_hours:
    print(f'task: this script only runs during hours: {run_hours}')
    exit()
else:
    print('task: going to get mini')
    bot_functions.get_mini(send_to_bq=True)
    print('task: got mini and sent to BigQuery')