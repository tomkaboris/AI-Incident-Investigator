from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    organization_name: str = Field(min_length=2, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str
    organization_name: str
    onboarding_completed: bool
    created_at: datetime


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    joined_at: datetime


class AddTeamMemberRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    temporary_password: str = Field(min_length=10, max_length=128)
    role: str = "investigator"
