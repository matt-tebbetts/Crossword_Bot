import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(var_name):
    """Retrieve the value of an environment variable."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Environment variable '{var_name}' not found.")
    return value

credentials = {
    'SQL_USER': get_env_variable('SQLUSER'),
    'SQL_PASS': get_env_variable('SQLPASS'),
    'SQL_HOST': get_env_variable('SQLHOST'),
    'SQL_PORT': get_env_variable('SQLPORT'),
    'SQL_DATA': get_env_variable('SQLDATA'),
    'NYT_COOKIE': get_env_variable('NYT_COOKIE')
}

sql_addr = f"mysql+pymysql://{credentials['SQL_USER']}:{credentials['SQL_PASS']}@{credentials['SQL_HOST']}:{credentials['SQL_PORT']}/{credentials['SQL_DATA']}"