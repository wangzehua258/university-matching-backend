#!/usr/bin/env python3
"""
Script to populate the database with sample data for development and testing.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from db.mongo import connect_to_mongo, close_mongo_connection

async def populate_database():
    """Populate the database with sample data."""
    print("🚀 Starting database population...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    from db.mongo import db
    
    try:
        # Clear existing data
        print("🧹 Clearing existing data...")
        await db.users.delete_many({})
        await db.universities.delete_many({})
        await db.parent_evaluations.delete_many({})
        await db.student_personality_tests.delete_many({})
        
        # 1. Insert Sample Users
        print("👥 Creating sample users...")
        users_data = [
            {
                "username": "student001",
                "email": "student001@example.com",
                "created_at": datetime.now(timezone.utc) - timedelta(days=30),
                "is_anonymous": False
            },
            {
                "username": "student002", 
                "email": "student002@example.com",
                "created_at": datetime.now(timezone.utc) - timedelta(days=25),
                "is_anonymous": False
            },
            {
                "username": "parent001",
                "email": "parent001@example.com", 
                "created_at": datetime.now(timezone.utc) - timedelta(days=20),
                "is_anonymous": False
            }
        ]
        
        user_results = await db.users.insert_many(users_data)
        user_ids = [str(result) for result in user_results.inserted_ids]
        print(f"✅ Created {len(user_ids)} users")
        
        # 2. Insert Sample Universities
        print("🏫 Creating sample universities...")
        universities_data = [
            {
                "name": "Stanford University",
                "country": "United States",
                "state": "California",
                "rank": 2,
                "tuition": 56000,
                "intlRate": 0.23,  # Use alias
                "type": "private",
                "strengths": ["Computer Science", "Engineering", "Business"],
                "gptSummary": "World-renowned private research university known for innovation and entrepreneurship. Located in the heart of Silicon Valley, Stanford offers exceptional programs in technology, engineering, and business with strong industry connections.",
                "location": "Stanford, CA",
                "personality_types": ["INTJ", "ENTP", "ENTJ"],
                "schoolSize": "Medium",
                "description": "World-renowned private research university known for innovation and entrepreneurship."
            },
            {
                "name": "MIT (Massachusetts Institute of Technology)",
                "country": "United States", 
                "state": "Massachusetts",
                "rank": 1,
                "tuition": 58000,
                "intlRate": 0.29,  # Use alias
                "type": "private",
                "strengths": ["Engineering", "Computer Science", "Physics"],
                "gptSummary": "Leading institution for science and technology education. MIT is known for its rigorous academic programs, cutting-edge research, and innovative approach to problem-solving in engineering and sciences.",
                "location": "Cambridge, MA",
                "personality_types": ["INTJ", "INTP", "ENTJ"],
                "schoolSize": "Medium",
                "description": "Leading institution for science and technology education."
            },
            {
                "name": "Harvard University",
                "country": "United States",
                "state": "Massachusetts",
                "rank": 3,
                "tuition": 55000,
                "intlRate": 0.25,  # Use alias
                "type": "private",
                "strengths": ["Law", "Business", "Medicine"],
                "gptSummary": "Ivy League university with strong liberal arts and professional programs. Harvard offers world-class education in law, business, medicine, and humanities with extensive resources and global recognition.",
                "location": "Cambridge, MA",
                "personality_types": ["ENTJ", "INTJ", "ENFJ"],
                "schoolSize": "Medium",
                "description": "Ivy League university with strong liberal arts and professional programs."
            },
            {
                "name": "University of California, Berkeley",
                "country": "United States",
                "state": "California",
                "rank": 4,
                "tuition": 45000,
                "intlRate": 0.18,  # Use alias
                "type": "public",
                "strengths": ["Computer Science", "Engineering", "Environmental Science"],
                "gptSummary": "Top public university known for research and innovation. UC Berkeley combines academic excellence with social consciousness, offering strong programs in technology, engineering, and environmental sciences.",
                "location": "Berkeley, CA",
                "personality_types": ["ENTP", "INTJ", "ENFP"],
                "schoolSize": "Large",
                "description": "Top public university known for research and innovation."
            },
            {
                "name": "University of Oxford",
                "country": "United Kingdom",
                "state": "England",
                "rank": 5,
                "tuition": 40000,
                "intlRate": 0.42,  # Use alias
                "type": "public",
                "strengths": ["Humanities", "Social Sciences", "Medicine"],
                "gptSummary": "World's oldest English-speaking university with rich academic tradition. Oxford offers exceptional programs in humanities, social sciences, and medicine with a unique tutorial system and historic campus.",
                "location": "Oxford, England",
                "personality_types": ["INTJ", "ENFJ", "INFP"],
                "schoolSize": "Medium",
                "description": "World's oldest English-speaking university with rich academic tradition."
            },
            {
                "name": "Tsinghua University",
                "country": "China",
                "state": "Beijing",
                "rank": 15,
                "tuition": 8000,
                "intlRate": 0.12,  # Use alias
                "type": "public",
                "strengths": ["Engineering", "Computer Science", "Architecture"],
                "gptSummary": "Leading Chinese university known for engineering and technology. Tsinghua offers world-class programs in engineering and computer science with strong research facilities and industry partnerships.",
                "location": "Beijing, China",
                "personality_types": ["INTJ", "ENTJ", "ISTJ"],
                "schoolSize": "Large",
                "description": "Leading Chinese university known for engineering and technology."
            },
            {
                "name": "University of Toronto",
                "country": "Canada",
                "state": "Ontario",
                "rank": 18,
                "tuition": 35000,
                "intlRate": 0.22,  # Use alias
                "type": "public",
                "strengths": ["Medicine", "Business", "Computer Science"],
                "gptSummary": "Canada's top university with strong research programs. U of T offers excellent programs in medicine, business, and computer science with a diverse, multicultural campus environment.",
                "location": "Toronto, Canada",
                "personality_types": ["ENFP", "INTJ", "ENTP"],
                "schoolSize": "Large",
                "description": "Canada's top university with strong research programs."
            },
            {
                "name": "National University of Singapore (NUS)",
                "country": "Singapore",
                "state": "Singapore",
                "rank": 8,
                "tuition": 15000,
                "intlRate": 0.35,  # Use alias
                "type": "public",
                "strengths": ["Engineering", "Business", "Computer Science"],
                "gptSummary": "Leading Asian university with strong global reputation. NUS offers excellent programs in engineering, business, and computer science with strong international partnerships and modern facilities.",
                "location": "Singapore",
                "personality_types": ["ENTJ", "INTJ", "ESTJ"],
                "schoolSize": "Large",
                "description": "Leading Asian university with strong global reputation."
            }
        ]
        
        university_results = await db.universities.insert_many(universities_data)
        university_ids = [str(result) for result in university_results.inserted_ids]
        print(f"✅ Created {len(university_ids)} universities")
        
        # 3. Insert Sample Student Personality Tests
        print("🧠 Creating sample personality tests...")
        personality_tests_data = [
            {
                "user_id": user_ids[0],
                "answers": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],  # INTJ pattern
                "personality_type": "INTJ",
                "recommended_universities": [university_ids[0], university_ids[1], university_ids[2]],
                "gpt_summary": "Student shows strong analytical and strategic thinking. INTJ personality type indicates preference for structured learning environments and research-oriented programs.",
                "created_at": datetime.now(timezone.utc) - timedelta(days=15)
            },
            {
                "user_id": user_ids[1],
                "answers": [2, 1, 2, 1, 2, 1, 2, 1, 2, 1],  # ENTP pattern
                "personality_type": "ENTP",
                "recommended_universities": [university_ids[3], university_ids[4], university_ids[7]],
                "gpt_summary": "Student demonstrates innovative thinking and adaptability. ENTP personality suggests they would thrive in dynamic, creative academic environments.",
                "created_at": datetime.now(timezone.utc) - timedelta(days=10)
            }
        ]
        
        test_results = await db.student_personality_tests.insert_many(personality_tests_data)
        print(f"✅ Created {len(test_results.inserted_ids)} personality tests")
        
        # 4. Insert Sample Parent Evaluations
        print("👨‍👩‍👧‍👦 Creating sample parent evaluations...")
        parent_evaluations_data = [
            {
                "user_id": user_ids[2],
                "child_age": 17,
                "child_grade": "12th Grade",
                "academic_interests": ["Computer Science", "Mathematics"],
                "extracurricular_activities": ["Coding Club", "Math Team", "Robotics"],
                "learning_style": "Visual and hands-on",
                "career_goals": "Software Engineering",
                "budget_range": "50000-70000",
                "location_preferences": ["United States", "Canada"],
                "university_size_preference": "Medium to Large",
                "recommended_universities": [university_ids[0], university_ids[1], university_ids[3]],
                "gpt_summary": "Based on the child's strong technical aptitude and interest in computer science, we recommend top-tier engineering programs with strong industry connections.",
                "created_at": datetime.now(timezone.utc) - timedelta(days=5)
            }
        ]
        
        eval_results = await db.parent_evaluations.insert_many(parent_evaluations_data)
        print(f"✅ Created {len(eval_results.inserted_ids)} parent evaluations")
        
        print("\n🎉 Database population completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Users: {len(user_ids)}")
        print(f"   - Universities: {len(university_ids)}")
        print(f"   - Personality Tests: {len(test_results.inserted_ids)}")
        print(f"   - Parent Evaluations: {len(eval_results.inserted_ids)}")
        
        # Show some sample data
        print(f"\n🔍 Sample Data Preview:")
        print(f"   - First University: {universities_data[0]['name']} (Rank: {universities_data[0]['rank']})")
        print(f"   - First User: {users_data[0]['username']}")
        print(f"   - First Test: {personality_tests_data[0]['personality_type']} personality type")
        
    except Exception as e:
        print(f"❌ Error populating database: {e}")
        raise
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(populate_database()) 