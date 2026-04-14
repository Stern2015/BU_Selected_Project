"""
Auth Service, Handles business logic related to authentication
"""

from driver.sql_executor import SQL_Executor
from dao.UserDAO import UserDAO

# Role Bitmasks
ROLE_CUSTOMER = 1
ROLE_VENDOR = 2
ROLE_ADMIN = 4

# user class for user info retreive
class User:
    def __init__(self, id, username, password, phone_number, role):
        self.id = id
        self.username = username
        self.password = password
        self.phone_number = phone_number
        self.role = role
    
    def get_user_name(self):
        return self.username
    
    def get_phone_number(self):
        return self.phone_number
    
    def get_role(self):
        return self.role
    
    def is_admin(self):
        return self.role & ROLE_ADMIN
    
    def is_vendor(self):
        return self.role & ROLE_VENDOR
    
    def get_dict(self):
        return {'id': self.id, 'username': self.username, 'password': self.password, 'role': self.role, "phone_number": self.phone_number}


#auth service , for verification user password and role check
class Auth_Service:
    def __init__(self):
        self.sql_executor = SQL_Executor()

    def verify_user_account(self, username, password):
        ##direct use raw password for easy insert sample data
        #if in production scenario, should hash password for security
        password_hash = password  
        userdao = UserDAO()

        result = userdao.get_user_by_username(username)
        if result:
            if result['PasswordHash'] == password_hash:

                return True
        return False
    
    #to get user account info for other user,return User instances
    def get_user_info(self, username):
        userdao = UserDAO()
        result = userdao.get_user_by_username(username)
        if result:
            user = User(result['User_ID'], result['Username'], result['PasswordHash'], result['Phone_Number'], result['Role_Bits'])
            
            return user
        
        return None
    
    @staticmethod
    def check_vendor_role(user):
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & ROLE_VENDOR)
    
    @staticmethod
    def check_admin_role(user):
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & ROLE_ADMIN)
    
    @staticmethod
    def check_customer_role(user):
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & ROLE_CUSTOMER)
    
    @staticmethod
    def has_role(user, role_flag):
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & role_flag)
        
