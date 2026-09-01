from sqlalchemy import create_engine

engine = create_engine(
    "mysql+pymysql://root:root@localhost:3306/telecom_project_1"
)