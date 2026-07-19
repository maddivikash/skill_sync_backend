from pydantic import BaseModel, EmailStr, constr

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: constr(min_length=6)

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    current_password: str
    new_password: constr(min_length=6)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: constr(min_length=6)

