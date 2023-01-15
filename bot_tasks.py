import bot_functions
import pytz
from datetime import datetime

now = datetime.now(pytz.timezone('US/Eastern'))
now_ts = now.strftime("%Y-%m-%d %H:%M:%S")
print(f'current time is: {now_ts} (Hour {now.hour})')

# set hours
run_hours = [0, 2, 4, 6, 8, 10, 12, 16, 17, 20, 21, 23] # really only need 17 (5:59pm) and 21 (9:59pm)

if now.hour not in run_hours:
    print(f'task: this script only runs during hours: {run_hours}')
else:
    print('task: running get_mini')
    bot_functions.get_mini()