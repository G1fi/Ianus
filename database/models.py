from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String(30), nullable=False)
    first_name: Mapped[str] = mapped_column(String(30), nullable=False)
    middle_name: Mapped[str] = mapped_column(String(30), nullable=False)
    subgroup: Mapped[int] = mapped_column(default=0, nullable=False)

    attendances: Mapped['Attendance'] = relationship(order_by='Attendance.id', back_populates="user")


class Attendance(Base):
    __tablename__ = 'attendance'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(nullable=False) 
    lecture_number: Mapped[int] = mapped_column(nullable=False)
    user_id = mapped_column(ForeignKey("users.id"))
    
    challenge: Mapped[str] = mapped_column(String(50), nullable=False)
    video_path: Mapped[str] = mapped_column(String(50), nullable=False)
    
    user: Mapped[User] = relationship(back_populates="attendances")
