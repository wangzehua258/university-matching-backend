from fastapi import APIRouter, HTTPException
from typing import List, Optional
from bson import ObjectId

from models.evaluation import ParentEvaluation, ParentEvaluationCreate, ParentEvaluationResponse
from models.personality import StudentTest, StudentTestCreate, StudentTestResponse
from db.mongo import get_db
from gpt.recommend_schools import recommend_schools_for_parent, classify_applications, generate_student_profile, generate_application_strategy
from gpt.generate_reason import generate_parent_evaluation_summary

router = APIRouter()

@router.post("/parent")
async def create_parent_evaluation(eval_data: ParentEvaluationCreate):
    """创建家长评估"""
    try:
        db = get_db()
        
        if db is None:
            # 如果全局数据库连接不可用，创建新的连接
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient('mongodb://localhost:27017')
            db = client.university_matcher
        
        print(f"开始处理评估请求，用户ID: {eval_data.user_id}")
        
        # 推荐学校
        recommended_school_ids = await recommend_schools_for_parent(eval_data.input)
        print(f"推荐学校ID: {recommended_school_ids}")
        
        # 获取推荐学校的详细信息
        school_ids = [ObjectId(school_id) for school_id in recommended_school_ids]
        schools = await db.universities.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
        print(f"找到 {len(schools)} 所学校")
        
        # 生成GPT评估总结
        gpt_summary = await generate_parent_evaluation_summary(eval_data.input, recommended_school_ids)
        print("GPT总结生成完成")
        
        # 创建评估记录
        evaluation = ParentEvaluation(
            user_id=eval_data.user_id,
            input=eval_data.input,
            recommended_schools=recommended_school_ids,
            gpt_summary=gpt_summary
        )
        
        result = await db.parent_evaluations.insert_one(evaluation.dict(by_alias=True))
        evaluation.id = result.inserted_id
        print(f"评估记录已保存，ID: {evaluation.id}")
        
        # 构建返回给前端的数据结构
        recommended_schools = []
        for school in schools:
            recommended_schools.append({
                "id": str(school["_id"]),
                "name": school["name"],
                "country": school["country"],
                "rank": school["rank"],
                "tuition": school["tuition"],
                "intl_rate": school.get("intlRate", 0),
                "type": school["type"],
                "schoolSize": school.get("schoolSize", "medium"),
                "strengths": school["strengths"],
                "tags": school.get("tags", []),
                "has_internship_program": school.get("has_internship_program", False),
                "has_research_program": school.get("has_research_program", False),
                "gpt_summary": school.get("gptSummary", ""),
                "logoUrl": school.get("logoUrl", ""),
                "acceptanceRate": school.get("acceptanceRate", 0),
                "satRange": school.get("satRange", ""),
                "actRange": school.get("actRange", ""),
                "gpaRange": school.get("gpaRange", ""),
                "applicationDeadline": school.get("applicationDeadline", ""),
                "website": school.get("website", "")
            })
        
        # 分类申请策略
        ed_suggestion, ea_suggestions, rd_suggestions = classify_applications(recommended_schools)
        
        # 生成学生画像
        student_profile = generate_student_profile(eval_data.input)
        
        # 生成申请策略
        strategy = generate_application_strategy(eval_data.input, len(recommended_schools))
        
        response_data = {
            "id": str(evaluation.id),
            "user_id": str(evaluation.user_id),
            "studentProfile": student_profile,
            "recommendedSchools": recommended_schools,
            "edSuggestion": ed_suggestion,
            "eaSuggestions": ea_suggestions,
            "rdSuggestions": rd_suggestions,
            "strategy": strategy,
            "gptSummary": gpt_summary,
            "created_at": evaluation.created_at
        }
        
        print("响应数据构建完成")
        return response_data
        
    except Exception as e:
        print(f"处理评估请求时出错: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理评估请求时出错: {str(e)}")

@router.get("/parent/{eval_id}", response_model=dict)
async def get_parent_evaluation(eval_id: str):
    """获取家长评估结果"""
    db = get_db()
    
    try:
        eval_obj_id = ObjectId(eval_id)
    except:
        raise HTTPException(status_code=400, detail="无效的评估ID")
    
    evaluation = await db.parent_evaluations.find_one({"_id": eval_obj_id})
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估不存在")
    
    # 获取推荐学校的详细信息
    school_ids = [ObjectId(school_id) for school_id in evaluation["recommended_schools"]]
    schools = await db.universities.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
    
    # 构建返回给前端的数据结构
    recommended_schools = []
    for school in schools:
        recommended_schools.append({
            "id": str(school["_id"]),
            "name": school["name"],
            "country": school["country"],
            "rank": school["rank"],
            "tuition": school["tuition"],
            "intl_rate": school.get("intlRate", 0),
            "type": school["type"],
            "schoolSize": school.get("schoolSize", "medium"),
            "strengths": school["strengths"],
            "tags": school.get("tags", []),
            "has_internship_program": school.get("has_internship_program", False),
            "has_research_program": school.get("has_research_program", False),
            "gpt_summary": school.get("gptSummary", ""),
            "logoUrl": school.get("logoUrl", ""),
            "acceptanceRate": school.get("acceptanceRate", 0),
            "satRange": school.get("satRange", ""),
            "actRange": school.get("actRange", ""),
            "gpaRange": school.get("gpaRange", ""),
            "applicationDeadline": school.get("applicationDeadline", ""),
            "website": school.get("website", "")
        })
    
    # 分类申请策略
    ed_suggestion, ea_suggestions, rd_suggestions = classify_applications(recommended_schools)
    
    # 生成学生画像
    student_profile = generate_student_profile(evaluation["input"])
    
    # 生成申请策略
    strategy = generate_application_strategy(evaluation["input"], len(recommended_schools))
    
    return {
        "id": str(evaluation["_id"]),
        "user_id": str(evaluation["user_id"]),
        "studentProfile": student_profile,
        "recommendedSchools": recommended_schools,
        "edSuggestion": ed_suggestion,
        "eaSuggestions": ea_suggestions,
        "rdSuggestions": rd_suggestions,
        "strategy": strategy,
        "gptSummary": evaluation["gpt_summary"],
        "created_at": evaluation["created_at"]
    }

@router.get("/parent/user/{user_id}", response_model=List[ParentEvaluationResponse])
async def get_parent_evaluations_by_user(user_id: str):
    """根据用户ID获取家长评估结果列表"""
    db = get_db()
    
    evaluations = await db.parent_evaluations.find({"user_id": user_id}).sort("created_at", -1).to_list(length=None)
    
    return [
        ParentEvaluationResponse(
            id=str(eval["_id"]),
            user_id=str(eval["user_id"]),
            input=eval["input"],
            recommended_schools=[str(school_id) for school_id in eval["recommended_schools"]],
            ed_suggestion=str(eval["ed_suggestion"]) if eval.get("ed_suggestion") else None,
            ea_suggestions=[str(school_id) for school_id in eval.get("ea_suggestions", [])],
            rd_suggestions=[str(school_id) for school_id in eval.get("rd_suggestions", [])],
            gpt_summary=eval["gpt_summary"],
            created_at=eval["created_at"]
        )
        for eval in evaluations
    ]

@router.post("/student", response_model=StudentTestResponse)
async def create_student_test(test_data: StudentTestCreate):
    """创建学生人格测评"""
    db = get_db()
    
    # 创建测评记录
    test = StudentTest(
        user_id=test_data.user_id,
        answers=test_data.answers,
        personality_type=test_data.personality_type,
        recommended_universities=test_data.recommended_universities,
        gpt_summary=test_data.gpt_summary
    )
    
    result = await db.student_personality_tests.insert_one(test.dict(by_alias=True))
    test.id = result.inserted_id
    
    return StudentTestResponse(
        id=str(test.id),
        user_id=str(test.user_id),
        answers=test.answers,
        personality_type=test.personality_type,
        recommended_universities=[str(uni_id) for uni_id in test.recommended_universities],
        gpt_summary=test.gpt_summary,
        created_at=test.created_at
    )

@router.get("/student/{test_id}", response_model=StudentTestResponse)
async def get_student_test(test_id: str):
    """获取学生人格测评结果"""
    db = get_db()
    
    try:
        test_obj_id = ObjectId(test_id)
    except:
        raise HTTPException(status_code=400, detail="无效的测评ID")
    
    test = await db.student_personality_tests.find_one({"_id": test_obj_id})
    if not test:
        raise HTTPException(status_code=404, detail="测评不存在")
    
    return StudentTestResponse(
        id=str(test["_id"]),
        user_id=str(test["user_id"]),
        answers=test["answers"],
        personality_type=test["personality_type"],
        recommended_universities=[str(uni_id) for uni_id in test["recommended_universities"]],
        gpt_summary=test["gpt_summary"],
        created_at=test["created_at"]
    )

@router.get("/student/user/{user_id}", response_model=List[StudentTestResponse])
async def get_student_tests_by_user(user_id: str):
    """根据用户ID获取学生测评结果列表"""
    db = get_db()
    
    tests = await db.student_personality_tests.find({"user_id": user_id}).sort("created_at", -1).to_list(length=None)
    
    return [
        StudentTestResponse(
            id=str(test["_id"]),
            user_id=str(test["user_id"]),
            answers=test["answers"],
            personality_type=test["personality_type"],
            recommended_universities=[str(uni_id) for uni_id in test["recommended_universities"]],
            gpt_summary=test["gpt_summary"],
            created_at=test["created_at"]
        )
        for test in tests
    ] 