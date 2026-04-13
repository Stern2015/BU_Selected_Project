from dao.BaseDAO import BaseDAO

class UserDAO(BaseDAO):
    def __init__(self):
        super().__init__()

    def get_user_by_username(self, username):
        sql = "SELECT User_ID, Username, PasswordHash, Phone_Number, Role_Bits FROM UserAccount WHERE Username = %s"
        params = (username,)
        result = self.executor.execute_query_one(sql, params)
        return result

    def get_all_users(self):
        sql = "SELECT User_ID as id, Username as username, PasswordHash as password, Role_Bits as role FROM UserAccount"
        return self.executor.execute_query(sql)