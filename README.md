# Guidance

## 1. Environment Setting

Start Anaconda Promt and execute below commands with requirements.txt: 
```
conda create --name database_system --file requirements.txt
conda activate database_system
```
## 2. Create databse
create a new databse schema named bu_selected, set charset as utf8mb4
```
CREATE SCHEMA `bu_selected` DEFAULT CHARACTER SET utf8mb4 ;
```

```
Then execute setup.sql, in order to create relation tables, triggers, procedures and insert sample data.
```

## 3. Run App
Before run app, please set databse connection parameters in config.ini and make sure db connection is tested pass.
default setting is like below:

```
[Database]
Host = localhost
User = root
Password = 123456
Name = bu_selected
Charset = utf8mb4
```

At last run app using this command:
```
python app.py
```

# Code Description

```
Layer 1 UI: app.py + templates
Layer 2 Business Implemention: services
Layer 3 Data Access Layer: dao + driver
Layer 4 Database: Mysql
```