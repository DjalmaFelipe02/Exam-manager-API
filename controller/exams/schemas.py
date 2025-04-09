# schemas.py
from ninja import Schema
from pydantic import Field, validator
from typing import Optional, List
from datetime import datetime

# ----------------------------------- Exam Schemas -----------------------------------
class ExamIn(Schema):
    title: str = Field(..., min_length=3, max_length=255)
    description: str
    is_active: bool = True
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: int = Field(..., gt=0, description="Duração em minutos")
    max_attempts: int = Field(1, gt=0)

    @validator('end_time')
    def validate_dates(cls, v, values):
        if v and values['start_time'] and v <= values['start_time']:
            raise ValueError('A data final deve ser após a data inicial')
        return v

class ExamOut(Schema):
    id: int
    title: str
    description: str
    is_active: bool
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration: int
    max_attempts: int
    created_by_id: int
    created_at: datetime
    updated_at: datetime

class ExamUpdate(Schema):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = Field(None, gt=0)
    max_attempts: Optional[int] = Field(None, gt=0)

# -------------------------------- Question Schemas --------------------------------
class QuestionIn(Schema):
    exam_id: int
    text: str = Field(..., min_length=5)
    points: int = Field(1, gt=0)
    question_type: str = Field('MCQ', pattern=r'^(MCQ|TF|SA)$')

class QuestionOut(Schema):
    id: int
    exam_id: int
    text: str
    points: int
    question_type: str
    explanation: Optional[str]

# --------------------------------- Choice Schemas ---------------------------------
class ChoiceIn(Schema):
    question_id: int
    text: str = Field(..., min_length=1)
    is_correct: bool = False
    order: Optional[int] = 0

class ChoiceOut(Schema):
    id: int
    question_id: int
    text: str
    is_correct: bool
    order: int

# ------------------------------- Participant Schemas -------------------------------
class ParticipantIn(Schema):
    exam_id: int

class ParticipantOut(Schema):
    id: int
    user_id: int
    exam_id: int
    score: float
    rank: Optional[int]
    current_attempt: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

# ---------------------------------- Answer Schemas ---------------------------------
class AnswerIn(Schema):
    question_id: int
    choice_id: int

class AnswerOut(Schema):
    id: int
    participant_id: int
    question_id: int
    choice_id: int
    is_correct: bool
    response_time: int
    answered_at: datetime

# ----------------------------------- Pagination -----------------------------------
class Pagination(Schema):
    count: int
    page: int
    per_page: int
    results: list

# -------------------------------- Error Responses --------------------------------
class ErrorResponse(Schema):
    detail: str