import os
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import Session
from .models import Base

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/attendance.db'))
engine = create_engine(f'sqlite:///{db_path}')

Base.metadata.create_all(engine)
session = Session(engine)

and_ = and_
or_ = or_