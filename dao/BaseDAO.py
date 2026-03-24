from driver.sql_executor import SQL_Executor
from driver.transaction_manager import Transaction_Manager

class BaseDAO:
    def __init__(self):
        self.executor = SQL_Executor()
        self.tx_manager = Transaction_Manager()
