"""
Transaction Manager
处理数据库事务管理
"""
from db_connection import Connection_Manager

class Transaction_Manager:
    def __init__(self):
        self.conn_manager = Connection_Manager()

    def execute_transaction(self, operations):
        conn = self.conn_manager.get_connection()

        try:
            with conn.cursor as cursor:
                conn.autocommit(False)
                for sql, params in operations:
                    cursor.execute(sql, params)

            conn.commit()
            return True
        except Exception as e:
            print(f"transaction failed, rolling back database. Detailed Error:{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
