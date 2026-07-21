from pydantic import BaseModel
from typing import List, Optional

class ExamSchedule(BaseModel):
    course_code: str
    course_name: str
    date: str
    time: str
    venue: str
    seat_no: Optional[str] = None

class AcademicResult(BaseModel):
    course_code: str
    assessment: str
    score: str
    grade: str
    remarks: Optional[str] = None

class StudentProfile(BaseModel):
    student_id: str
    full_name: str
    status: str = "Active"  # "Active", "Alumnus", "Suspended"
    enrollments: List[str] = []
    upcoming_exams: List[ExamSchedule] = []
    recent_results: List[AcademicResult] = []
    certificates_available: List[str] = []
    convocation_date: Optional[str] = None


def get_student_profile_json(student_id: str = "2026-CS-64"):
    mock_db = {
        "2026-CS-64": StudentProfile(
            student_id="2026-CS-64",
            full_name="Wasif Shuja",
            status="Active",
            enrollments=[
                "CS-301: Database Systems",
                "CS-305: Software Engineering",
                "AI-401: Artificial Intelligence"
            ],
            upcoming_exams=[
                ExamSchedule(
                    course_code="CS-301",
                    course_name="Database Systems Midterm",
                    date="2026-08-05",
                    time="10:00 AM - 12:00 PM",
                    venue="Lab 3, CS Department",
                    seat_no="S-42"
                ),
                ExamSchedule(
                    course_code="AI-401",
                    course_name="Artificial Intelligence Quiz 2",
                    date="2026-08-12",
                    time="02:00 PM - 03:00 PM",
                    venue="Hall B",
                    seat_no="H-18"
                )
            ],
            recent_results=[
                AcademicResult(
                    course_code="CS-305",
                    assessment="Software Architecture Assignment 1",
                    score="92/100",
                    grade="A",
                    remarks="Excellent design patterns implementation"
                ),
                AcademicResult(
                    course_code="CS-301",
                    assessment="SQL Query Optimization Quiz",
                    score="88/100",
                    grade="A-",
                    remarks="Good index optimization logic"
                )
            ],
            certificates_available=["Web Development Fundamentals (May 2026)"]
        ),
        
        "2022-CS-10": StudentProfile(
            student_id="2022-CS-10",
            full_name="Ali Khan", 
            status="Alumnus", 
            enrollments=[], 
            upcoming_exams=[],
            recent_results=[],
            convocation_date="October 15, 2026 at Main Auditorium"
        )
    }

    # Fetch profile or default to empty structure
    student = mock_db.get(student_id)
    if not student:
        return "{}"

    return student.model_dump_json(indent=2, exclude_none=True)