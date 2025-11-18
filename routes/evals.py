from fastapi import APIRouter, HTTPException
from typing import List, Optional
from bson import ObjectId

from models.evaluation import ParentEvaluation, ParentEvaluationCreate, ParentEvaluationResponse
from models.personality import StudentTest, StudentTestCreate, StudentTestResponse
from db.mongo import get_db
from gpt.recommend_schools import recommend_schools_for_parent, classify_applications, generate_student_profile, generate_application_strategy
from gpt.au_evaluation import apply_au_filters_and_score
from gpt.uk_evaluation import apply_uk_filters_and_score
from gpt.sg_evaluation import apply_sg_filters_and_score
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
        
        schools = []
        recommended_school_ids: list[str] = []
        # 分国家处理 - AU/UK/SG 将走各自逻辑文件；USA 维持旧逻辑
        country = eval_data.input.target_country
        print(f"🔍 DEBUG: country = '{country}', type = {type(country)}")
        fallback_info = None  # AU/UK/SG使用
        if country == "Australia":
            print("✅ 进入Australia分支 - 开始处理AU评估")
            # 从 AU 集合取原始数据
            au_docs = await db.university_au.find({"country": "Australia"}).to_list(length=None)
            if au_docs is None:
                au_docs = []
            print(f"📊 找到 {len(au_docs)} 所澳洲大学")
            # 打分排序（新版本支持回退策略）
            try:
                scored, fallback_info = apply_au_filters_and_score(eval_data.input.dict(), au_docs, enable_fallback=True)
                print(f"📊 评分后得到 {len(scored)} 所学校")
            except Exception as e:
                print(f"⚠️ 评分过程出错: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"评分过程出错: {str(e)}")
            # 取前5所
            top = scored[:5] if scored else []
            recommended_school_ids = [s["id"] for s in top if "id" in s]
            if not recommended_school_ids:
                print("⚠️ 没有推荐学校，使用兜底逻辑")
                # 兜底：返回排名前5的学校
                all_au = await db.university_au.find({"country": "Australia"}).to_list(length=None)
                if all_au:
                    sorted_by_rank = sorted(all_au, key=lambda x: int(x.get("rank", 9999) or 9999))
                    schools = sorted_by_rank[:5]
                    recommended_school_ids = [str(s.get("_id")) for s in schools]
                else:
                    schools = []
            else:
                school_obj_ids = [ObjectId(x) for x in recommended_school_ids]
                schools = await db.university_au.find({"_id": {"$in": school_obj_ids}}).to_list(length=len(school_obj_ids))
        elif country == "United Kingdom":
            uk_docs = await db.university_uk.find({"country": "United Kingdom"}).to_list(length=None)
            scored, fallback_info = apply_uk_filters_and_score(eval_data.input.dict(), uk_docs, enable_fallback=True)
            top = scored[:5]
            recommended_school_ids = [s["id"] for s in top]
            school_obj_ids = [ObjectId(x) for x in recommended_school_ids]
            schools = await db.university_uk.find({"_id": {"$in": school_obj_ids}}).to_list(length=len(school_obj_ids))
        elif country == "Singapore":
            print("✅ 进入Singapore分支 - 开始处理SG评估")
            sg_docs = await db.university_sg.find({"country": "Singapore"}).to_list(length=None)
            print(f"📊 找到 {len(sg_docs)} 所新加坡大学")
            scored, fallback_info = apply_sg_filters_and_score(eval_data.input.dict(), sg_docs, enable_fallback=True)
            print(f"📊 评分后得到 {len(scored)} 所学校，fallback_applied: {fallback_info.get('applied', False) if fallback_info else False}")
            top = scored[:5]
            recommended_school_ids = [s["id"] for s in top]
            print(f"📊 推荐学校IDs: {recommended_school_ids}")
            school_obj_ids = [ObjectId(x) for x in recommended_school_ids]
            schools = await db.university_sg.find({"_id": {"$in": school_obj_ids}}).to_list(length=len(school_obj_ids))
            print(f"📊 从数据库获取到 {len(schools)} 所学校详情")
        else:
            # USA 或未指定 → 使用原有逻辑（US universities 集合）
            recommended_school_ids = await recommend_schools_for_parent(eval_data.input)
            school_ids = [ObjectId(school_id) for school_id in recommended_school_ids]
            schools = await db.universities.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
        
        # 生成学生画像、申请策略和专业建议
        try:
            student_profile = generate_student_profile(eval_data.input)
        except Exception as e:
            print(f"⚠️ 生成学生画像时出错: {e}")
            student_profile = {"type": "", "description": ""}
        
        try:
            strategy_text = generate_application_strategy(eval_data.input, len(recommended_school_ids))
        except Exception as e:
            print(f"⚠️ 生成申请策略时出错: {e}")
            strategy_text = ""
        
        try:
            gpt_summary = await generate_parent_evaluation_summary(eval_data.input, recommended_school_ids)
        except Exception as e:
            print(f"⚠️ 生成GPT总结时出错: {e}")
            gpt_summary = ""
        
        # 创建评估记录
        evaluation = ParentEvaluation(
            user_id=eval_data.user_id,
            input=eval_data.input,
            recommended_schools=recommended_school_ids,
            gpt_summary=gpt_summary,
            fallback_info=fallback_info if country in ["Australia", "United Kingdom", "Singapore"] else None  # 保存回退信息（AU/UK/SG）
        )
        
        # Convert to dict without the id field to avoid _id: null issue
        evaluation_dict = evaluation.dict(by_alias=True, exclude={'id'})
        result = await db.parent_evaluations.insert_one(evaluation_dict)
        evaluation.id = result.inserted_id
        print(f"评估记录已保存，ID: {evaluation.id}")
        
        # 构建返回给前端的数据结构（按国家映射字段）
        recommended_schools = []
        if country == "Australia":
            for school in schools:
                recommended_schools.append({
                    "id": str(school["_id"]),
                    "name": school.get("name", ""),
                    "country": school.get("country", "Australia"),
                    "rank": school.get("rank", 0),
                    "tuition": school.get("tuition_usd", 0),
                    "intlRate": school.get("intl_rate", 0),
                    "type": school.get("currency", "AUD"),
                    "schoolSize": None,
                    "strengths": school.get("strengths", []),
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("work_integrated_learning", False),
                    "has_research_program": False,
                    "gptSummary": "",
                    "logoUrl": None,
                    "acceptanceRate": None,
                    "satRange": None,
                    "actRange": None,
                    "gpaRange": None,
                    "applicationDeadline": school.get("intakes", ""),
                    "website": school.get("website", "")
                })
        elif country == "United Kingdom":
            for school in schools:
                recommended_schools.append({
                    "id": str(school["_id"]),
                    "name": school.get("name", ""),
                    "country": school.get("country", "United Kingdom"),
                    "rank": school.get("rank", 0),
                    "tuition": school.get("tuition_usd", 0),
                    "intlRate": school.get("intlRate", 0),
                    "type": "UK",
                    "schoolSize": None,
                    "strengths": school.get("strengths", []),
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("placement_year_available", False),
                    "has_research_program": False,
                    "gptSummary": "",
                    "logoUrl": None,
                    "acceptanceRate": None,
                    "satRange": None,
                    "actRange": None,
                    "gpaRange": None,
                    "applicationDeadline": school.get("ucas_deadline_type", ""),
                    "website": school.get("website", "")
                })
        elif country == "Singapore":
            for school in schools:
                recommended_schools.append({
                    "id": str(school["_id"]),
                    "name": school.get("name", ""),
                    "country": school.get("country", "Singapore"),
                    "rank": school.get("rank", 0),
                    "tuition": school.get("tuition_usd", 0),
                    "intlRate": school.get("intlRate", 0),
                    "type": "SG",
                    "schoolSize": None,
                    "strengths": school.get("strengths", []),
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("coop_or_internship_required", False),
                    "has_research_program": False,
                    "gptSummary": "",
                    "logoUrl": None,
                    "acceptanceRate": None,
                    "satRange": None,
                    "actRange": None,
                    "gpaRange": None,
                    "applicationDeadline": "",
                    "website": school.get("website", "")
                })
        else:
            for school in schools:
                recommended_schools.append({
                    "id": str(school["_id"]),
                    "name": school["name"],
                    "country": school["country"],
                    "rank": school["rank"],
                    "tuition": school["tuition"],
                    "intlRate": school.get("intlRate", 0),
                    "type": school["type"],
                    "schoolSize": school.get("schoolSize", "medium"),
                    "strengths": school["strengths"],
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("has_internship_program", False),
                    "has_research_program": school.get("has_research_program", False),
                    "gptSummary": school.get("gptSummary", ""),
                    "logoUrl": school.get("logoUrl", ""),
                    "acceptanceRate": school.get("acceptanceRate", 0),
                    "satRange": school.get("satRange", ""),
                    "actRange": school.get("actRange", ""),
                    "gpaRange": school.get("gpaRange", ""),
                    "applicationDeadline": school.get("applicationDeadline", ""),
                    "website": school.get("website", ""),
                    "supports_ed": school.get("supports_ed", False),
                    "supports_ea": school.get("supports_ea", False),
                    "supports_rd": school.get("supports_rd", False)
                })
        
        # 根据国家构建不同的返回结构
        print(f"🔍 构建返回结构 - 当前国家: {country}, 类型: {type(country)}")
        if country == "Australia":
            print("✅ 进入澳洲专用分支")
            # 澳洲专用结构：生成每所学校的详细解释
            from gpt.au_evaluation import generate_school_explanations
            input_dict = eval_data.input.dict()
            
            # 创建ID到score的映射
            score_map = {s["id"]: s.get("score", 0) for s in top if "id" in s}
            
            # 限制推荐学校数量为最多5所
            recommended_schools_limited = recommended_schools[:5]
            
            schools_with_explanations = []
            for school in recommended_schools_limited:
                school_id = school["id"]
                school_detail = next((s for s in schools if str(s.get("_id")) == school_id), None)
                
                if school_detail:
                    try:
                        explanation = generate_school_explanations(school_detail, input_dict)
                        schools_with_explanations.append({
                            **school,
                            "explanation": explanation,
                            "matchScore": score_map.get(school_id, 0),
                        })
                    except Exception as e:
                        print(f"生成AU学校解释时出错: {e}")
                        import traceback
                        traceback.print_exc()
                        schools_with_explanations.append({
                            **school,
                            "explanation": [],
                            "matchScore": score_map.get(school_id, 0),
                        })
                else:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": score_map.get(school_id, 0),
                    })
            
            response_data = {
                "id": str(evaluation.id),
                "user_id": str(evaluation.user_id),
                "targetCountry": "Australia",
                "recommendedSchools": schools_with_explanations,  # 已经是前5所了
                "fallbackInfo": fallback_info if fallback_info else {"applied": False, "steps": []},
                "applicationGuidance": {
                    "title": "澳洲大学申请流程说明",
                    "steps": [
                        "1. 准备材料：高中成绩单、英语成绩（IELTS/TOEFL/PTE）、个人陈述（部分学校需要）",
                        "2. 选择入学时间：多数学校提供2月和7月入学，部分提供3个学期",
                        "3. 直接申请：通过学校官网或授权代理申请（无需统一系统）",
                        "4. 语言班选项：如英语未达标，可申请语言/过渡课程，通过后进入正课",
                        "5. 接受Offer：收到录取后按要求缴纳押金并办理学生签证",
                        "6. 签证申请：准备资金证明、体检等材料，申请澳洲学生签证"
                    ],
                    "keyPoints": [
                        "申请时间灵活：通常提前3-6个月即可，部分热门专业需更早",
                        "英语成绩：大部分学校接受多种英语考试，可后补（部分专业除外）",
                        "申请费：多数学校申请免费或费用较低（约50-100澳元）"
                    ]
                },
                "keyInfoSummary": {
                    "budgetRange": f"推荐学校学费范围：${min([s.get('tuition', 0) for s in recommended_schools_limited] + [0]):,} - ${max([s.get('tuition', 0) for s in recommended_schools_limited] + [0]):,}/年（USD）" if recommended_schools_limited else "推荐学校学费范围：请查看具体学校信息",
                    "englishRequirement": "大部分学校要求IELTS 6.5（单项不低于6.0）或同等水平",
                    "intakeTiming": "主要入学时间：2月和7月",
                    "pswInfo": "毕业后可获得2-4年PSW工作签证（取决于学习时长和地区）"
                },
                "gptSummary": gpt_summary,
                "created_at": evaluation.created_at
            }
        elif country == "United Kingdom":
            # 英国专用结构：生成每所学校的详细解释
            from gpt.uk_evaluation import generate_school_explanations
            input_dict = eval_data.input.dict()
            
            # 创建ID到score的映射
            score_map = {s["id"]: s.get("score", 0) for s in top if "id" in s}
            
            schools_with_explanations = []
            for school in recommended_schools:
                school_id = school["id"]
                school_detail = next((s for s in schools if str(s.get("_id")) == school_id), None)
                
                if school_detail:
                    # 标记是否因回退加入
                    fallback_reason = ""
                    if fallback_info and fallback_info.get("applied"):
                        fallback_reason = "; ".join(fallback_info.get("steps", []))
                    explanation = generate_school_explanations(
                        school_detail,
                        {**input_dict, "_fallback_applied": fallback_info.get("applied") if fallback_info else False, "_fallback_reason": fallback_reason}
                    )
                    schools_with_explanations.append({
                        **school,
                        "explanation": explanation,
                        "matchScore": score_map.get(school_id, 0),
                    })
                else:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": score_map.get(school_id, 0),
                    })
            
            # 计算预算范围
            tuition_values = [s.get("tuition", 0) for s in recommended_schools if s.get("tuition", 0) > 0]
            budget_range = ""
            if tuition_values:
                budget_range = f"推荐学校学费范围：£{min(tuition_values):,} - £{max(tuition_values):,}/年（USD约${int(min(tuition_values) * 1.27):,} - ${int(max(tuition_values) * 1.27):,}）"
            else:
                budget_range = "推荐学校学费范围：请查看具体学校信息"
            
            response_data = {
                "id": str(evaluation.id),
                "user_id": str(evaluation.user_id),
                "targetCountry": "United Kingdom",
                "recommendedSchools": schools_with_explanations,
                "fallbackInfo": fallback_info if fallback_info else {"applied": False, "steps": []},
                "applicationGuidance": {
                    "title": "英国大学申请流程说明",
                    "steps": [
                        "1. 准备材料：A-Level/IB成绩、个人陈述（PS）、推荐信、入学测试（如Oxbridge/医学类）",
                        "2. UCAS申请：通过UCAS统一系统提交申请（最多5个志愿）",
                        "3. 申请时间：Oxbridge/医学类10月15日截止，常规路线1月31日截止",
                        "4. Foundation路线：如成绩不足，可先读预科或国际大一，再衔接本科",
                        "5. 等待Offer：收到条件录取或无条件录取",
                        "6. 选择确认：在UCAS上确认最终选择并满足条件",
                        "7. 签证申请：收到CAS后申请英国学生签证"
                    ],
                    "keyPoints": [
                        "UCAS系统：所有英国本科申请必须通过UCAS提交",
                        "申请费：单次申请费约£22.50（1个志愿）或£27（2-5个志愿）",
                        "Personal Statement：所有志愿共用一份，需精心准备",
                        "入学测试：Oxbridge、医学、部分专业需要额外测试（如STEP、BMAT等）",
                        "Foundation：成绩或科目不足时可考虑预科/国际大一，无需UCAS"
                    ]
                },
                "keyInfoSummary": {
                    "budgetRange": budget_range,
                    "ucasInfo": "主要申请时间：Oxbridge/医学类10/15，常规路线1/31",
                    "foundationInfo": "如成绩不足，可考虑Foundation/国际大一路线",
                    "visaInfo": "毕业后可申请PSW工作签证（本科/硕士2年，博士3年）"
                },
                "gptSummary": gpt_summary,
                "created_at": evaluation.created_at
            }
        elif country == "Singapore":
            print("✅ 进入新加坡专用返回结构分支")
            # 新加坡专用结构：生成每所学校的详细解释
            from gpt.sg_evaluation import generate_school_explanations
            input_dict = eval_data.input.dict()
            
            # 创建ID到score的映射
            score_map = {s["id"]: s.get("score", 0) for s in top if "id" in s}
            
            schools_with_explanations = []
            for school in recommended_schools:
                school_id = school["id"]
                school_detail = next((s for s in schools if str(s.get("_id")) == school_id), None)
                
                if school_detail:
                    # 标记是否因回退加入
                    fallback_reason = ""
                    if fallback_info and fallback_info.get("applied"):
                        fallback_reason = "; ".join(fallback_info.get("steps", []))
                    explanation = generate_school_explanations(
                        school_detail,
                        {**input_dict, "_fallback_applied": fallback_info.get("applied") if fallback_info else False, "_fallback_reason": fallback_reason}
                    )
                    schools_with_explanations.append({
                        **school,
                        "explanation": explanation,
                        "matchScore": score_map.get(school_id, 0),
                    })
                else:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": score_map.get(school_id, 0),
                    })
            
            # 计算预算范围
            tuition_values = [s.get("tuition", 0) for s in recommended_schools if s.get("tuition", 0) > 0]
            budget_range = ""
            if tuition_values:
                budget_range = f"推荐学校学费范围：S${min(tuition_values):,} - S${max(tuition_values):,}/年（USD约${int(min(tuition_values) * 0.74):,} - ${int(max(tuition_values) * 0.74):,}）"
            else:
                budget_range = "推荐学校学费范围：请查看具体学校信息"
            
            response_data = {
                "id": str(evaluation.id),
                "user_id": str(evaluation.user_id),
                "targetCountry": "Singapore",
                "recommendedSchools": schools_with_explanations,
                "fallbackInfo": fallback_info if fallback_info else {"applied": False, "steps": []},
                "applicationGuidance": {
                    "title": "新加坡大学申请流程说明",
                    "steps": [
                        "1. 准备材料：高中成绩单、英语成绩（IELTS/TOEFL/PTE）、个人陈述、推荐信",
                        "2. 提交申请：通过各大学官网直接申请（无需统一系统）",
                        "3. 申请时间：多数大学10-11月开始接受申请，次年1-3月截止",
                        "4. 面试/作品集：部分专业需要面试、作品集或小论文（需提前准备）",
                        "5. Tuition Grant（TG）：如申请TG，需签约毕业后在新加坡工作若干年",
                        "6. 等待Offer：收到录取通知（有条件/无条件）",
                        "7. 接受Offer：按要求缴纳押金确认录取",
                        "8. 学生签证：申请新加坡学生准证（Student Pass）"
                    ],
                    "keyPoints": [
                        "申请系统：各大学独立申请系统，需分别提交材料",
                        "申请费：多数大学申请费约S$10-50（约USD 7-37）",
                        "TG申请：可在接受Offer后申请Tuition Grant，降低学费但需履行Bond服务期",
                        "面试要求：部分热门专业（如医学、法律、设计）需要面试或作品集",
                        "双学位：部分大学提供双学位项目，需额外申请或满足条件"
                    ]
                },
                "keyInfoSummary": {
                    "budgetRange": budget_range,
                    "tgInfo": "Tuition Grant可大幅降低学费，但需签约在新加坡工作若干年",
                    "applicationTiming": "主要申请时间：10-11月开始，次年1-3月截止",
                    "visaInfo": "学生准证有效期通常覆盖整个学习期间，毕业后可申请工作准证"
                },
                "gptSummary": gpt_summary,
                "created_at": evaluation.created_at
            }
        else:
            # 其他国家（USA）使用原有结构
            ed_suggestion, ea_suggestions, rd_suggestions = classify_applications(recommended_schools)
            # 使用生成的学生画像和申请策略
            strategy = {"plan": strategy_text, "count": len(recommended_schools)}
            
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
    """获取家长评估结果（即使无推荐也返回正常结构）"""
    try:
        db = get_db()

        # 参数校验
        try:
            eval_obj_id = ObjectId(eval_id)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的评估ID")

        # 查询评估记录
        evaluation = await db.parent_evaluations.find_one({"_id": eval_obj_id})
        if not evaluation:
            raise HTTPException(status_code=404, detail="评估不存在")

        input_country = evaluation.get("input", {}).get("target_country", "USA")
        school_ids = [ObjectId(sid) for sid in evaluation.get("recommended_schools", [])]

        # 查询学校详情（按国家集合）
        schools = []
        if school_ids:
            if input_country == "Australia":
                schools = await db.university_au.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
            elif input_country == "United Kingdom":
                schools = await db.university_uk.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
            elif input_country == "Singapore":
                schools = await db.university_sg.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
            else:
                schools = await db.universities.find({"_id": {"$in": school_ids}}).to_list(length=len(school_ids))
    
        # 兜底逻辑：如果查询结果为空（无论是school_ids为空还是查询无结果），对于AU至少返回排名前5的学校
        if not schools and input_country == "Australia":
            print(f"⚠️ GET接口：评估ID {eval_id} 的推荐学校为空，执行兜底逻辑（返回排名前5的AU学校）")
            all_au = await db.university_au.find({"country": "Australia"}).to_list(length=None)
            if all_au:
                sorted_by_rank = sorted(all_au, key=lambda x: int(x.get("rank", 9999) or 9999))
                schools = sorted_by_rank[:5]

        # 映射为前端结构（限制最多5所）
        recommended_schools = []
        if input_country == "Australia":
            for school in schools[:5]:  # 限制最多5所
                recommended_schools.append({
                    "id": str(school.get("_id")),
                    "name": school.get("name", ""),
                    "country": school.get("country", "Australia"),
                    "rank": school.get("rank", 0),
                    "tuition": school.get("tuition_usd", 0),
                    "intlRate": school.get("intl_rate", 0),
                    "type": school.get("currency", "AUD"),
                    "schoolSize": None,
                    "strengths": school.get("strengths", []),
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("work_integrated_learning", False),
                    "has_research_program": False,
                    "gptSummary": "",
                    "logoUrl": None,
                    "acceptanceRate": None,
                    "satRange": None,
                    "actRange": None,
                    "gpaRange": None,
                    "applicationDeadline": school.get("intakes", ""),
                    "website": school.get("website", "")
                })
        elif input_country == "United Kingdom":
            for school in schools:
                recommended_schools.append({
                    "id": str(school.get("_id")),
                    "name": school.get("name", ""),
                    "country": school.get("country", "United Kingdom"),
                    "rank": school.get("rank", 0),
                    "tuition": school.get("tuition_usd", 0),
                    "intlRate": school.get("intlRate", 0),
                    "type": "UK",
                    "schoolSize": None,
                    "strengths": school.get("strengths", []),
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("placement_year_available", False),
                    "has_research_program": False,
                    "gptSummary": "",
                    "logoUrl": None,
                    "acceptanceRate": None,
                    "satRange": None,
                    "actRange": None,
                    "gpaRange": None,
                    "applicationDeadline": school.get("ucas_deadline_type", ""),
                    "website": school.get("website", "")
                })
        elif input_country == "Singapore":
            for school in schools:
                recommended_schools.append({
                    "id": str(school.get("_id")),
                    "name": school.get("name", ""),
                    "country": school.get("country", "Singapore"),
                    "rank": school.get("rank", 0),
                    "tuition": school.get("tuition_usd", 0),
                    "intlRate": school.get("intlRate", 0),
                    "type": "SG",
                    "schoolSize": None,
                    "strengths": school.get("strengths", []),
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("coop_or_internship_required", False),
                    "has_research_program": False,
                    "gptSummary": "",
                    "logoUrl": None,
                    "acceptanceRate": None,
                    "satRange": None,
                    "actRange": None,
                    "gpaRange": None,
                    "applicationDeadline": "",
                    "website": school.get("website", "")
                })
        else:
            for school in schools:
                recommended_schools.append({
                    "id": str(school.get("_id")),
                    "name": school.get("name", ""),
                    "country": school.get("country", "USA"),
                    "rank": school.get("rank", 0),
                    "tuition": school.get("tuition", 0),
                    "intlRate": school.get("intlRate", 0),
                    "type": school.get("type", "public"),
                    "schoolSize": school.get("schoolSize", "medium"),
                    "strengths": school.get("strengths", []),
                    "tags": school.get("tags", []),
                    "has_internship_program": school.get("has_internship_program", False),
                    "has_research_program": school.get("has_research_program", False),
                    "gptSummary": school.get("gptSummary", ""),
                    "logoUrl": school.get("logoUrl", ""),
                    "acceptanceRate": school.get("acceptanceRate", 0),
                    "satRange": school.get("satRange", ""),
                    "actRange": school.get("actRange", ""),
                    "gpaRange": school.get("gpaRange", ""),
                    "applicationDeadline": school.get("applicationDeadline", ""),
                    "website": school.get("website", ""),
                    "supports_ed": school.get("supports_ed", False),
                    "supports_ea": school.get("supports_ea", False),
                    "supports_rd": school.get("supports_rd", False)
                })

        # 根据国家返回不同结构
        if input_country == "United Kingdom":
            # 英国专用结构：生成解释和申请指导
            from gpt.uk_evaluation import generate_school_explanations
            input_dict = evaluation.get("input") or {}
            if not isinstance(input_dict, dict):
                input_dict = {}
            
            schools_with_explanations = []
            for school in recommended_schools:
                school_id = school.get("id")
                if not school_id:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": 0,
                    })
                    continue
                
                school_detail = next((s for s in schools if str(s.get("_id")) == school_id), None)
                
                if school_detail:
                    try:
                        fallback_info_db = evaluation.get("fallback_info") or {"applied": False, "steps": []}
                        if not isinstance(fallback_info_db, dict):
                            fallback_info_db = {"applied": False, "steps": []}
                        fallback_reason = "; ".join(fallback_info_db.get("steps", [])) if fallback_info_db.get("applied") else ""
                        explanation = generate_school_explanations(
                            school_detail,
                            {**input_dict, "_fallback_applied": fallback_info_db.get("applied", False), "_fallback_reason": fallback_reason}
                        )
                        schools_with_explanations.append({
                            **school,
                            "explanation": explanation,
                            "matchScore": 0,
                        })
                    except Exception as e:
                        print(f"生成UK学校解释时出错: {e}")
                        schools_with_explanations.append({
                            **school,
                            "explanation": [],
                            "matchScore": 0,
                        })
                else:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": 0,
                    })
            
            fallback_info = evaluation.get("fallback_info") or {"applied": False, "steps": []}
            if not isinstance(fallback_info, dict):
                fallback_info = {"applied": False, "steps": []}
            
            tuition_values = [s.get("tuition", 0) for s in recommended_schools if s.get("tuition", 0) > 0]
            budget_range = ""
            if tuition_values:
                budget_range = f"推荐学校学费范围：£{min(tuition_values):,} - £{max(tuition_values):,}/年（USD约${int(min(tuition_values) * 1.27):,} - ${int(max(tuition_values) * 1.27):,}）"
            else:
                budget_range = "推荐学校学费范围：请查看具体学校信息"
            
            return {
                "id": str(evaluation.get("_id")),
                "user_id": str(evaluation.get("user_id")),
                "targetCountry": "United Kingdom",
                "recommendedSchools": schools_with_explanations,
                "fallbackInfo": fallback_info,
                "applicationGuidance": {
                    "title": "英国大学申请流程说明",
                    "steps": [
                    "1. 准备材料：A-Level/IB成绩、个人陈述（PS）、推荐信、入学测试（如Oxbridge/医学类）",
                    "2. UCAS申请：通过UCAS统一系统提交申请（最多5个志愿）",
                    "3. 申请时间：Oxbridge/医学类10月15日截止，常规路线1月31日截止",
                    "4. Foundation路线：如成绩不足，可先读预科或国际大一，再衔接本科",
                    "5. 等待Offer：收到条件录取或无条件录取",
                    "6. 选择确认：在UCAS上确认最终选择并满足条件",
                    "7. 签证申请：收到CAS后申请英国学生签证"
                ],
                "keyPoints": [
                    "UCAS系统：所有英国本科申请必须通过UCAS提交",
                    "申请费：单次申请费约£22.50（1个志愿）或£27（2-5个志愿）",
                    "Personal Statement：所有志愿共用一份，需精心准备",
                    "入学测试：Oxbridge、医学、部分专业需要额外测试（如STEP、BMAT等）",
                    "Foundation：成绩或科目不足时可考虑预科/国际大一，无需UCAS"
                ]
            },
            "keyInfoSummary": {
                "budgetRange": budget_range,
                "ucasInfo": "主要申请时间：Oxbridge/医学类10/15，常规路线1/31",
                "foundationInfo": "如成绩不足，可考虑Foundation/国际大一路线",
                "visaInfo": "毕业后可申请PSW工作签证（本科/硕士2年，博士3年）"
            },
            "created_at": evaluation.get("created_at")
                }
        elif input_country == "Singapore":
            print("✅ GET接口：进入新加坡专用返回结构分支")
            # 新加坡专用结构：生成解释和申请指导
            from gpt.sg_evaluation import generate_school_explanations
            input_dict = evaluation.get("input") or {}
            if not isinstance(input_dict, dict):
                input_dict = {}
            
            schools_with_explanations = []
            for school in recommended_schools:
                school_id = school.get("id")
                if not school_id:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": 0,
                    })
                    continue
                
                school_detail = next((s for s in schools if str(s.get("_id")) == school_id), None)
                
                if school_detail:
                    try:
                        fallback_info_db = evaluation.get("fallback_info") or {"applied": False, "steps": []}
                        if not isinstance(fallback_info_db, dict):
                            fallback_info_db = {"applied": False, "steps": []}
                        fallback_reason = "; ".join(fallback_info_db.get("steps", [])) if fallback_info_db.get("applied") else ""
                        explanation = generate_school_explanations(
                            school_detail,
                            {**input_dict, "_fallback_applied": fallback_info_db.get("applied", False), "_fallback_reason": fallback_reason}
                        )
                        schools_with_explanations.append({
                            **school,
                            "explanation": explanation,
                            "matchScore": 0,
                        })
                    except Exception as e:
                        print(f"生成SG学校解释时出错: {e}")
                        schools_with_explanations.append({
                            **school,
                            "explanation": [],
                            "matchScore": 0,
                        })
                else:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": 0,
                    })
            
            fallback_info = evaluation.get("fallback_info") or {"applied": False, "steps": []}
            if not isinstance(fallback_info, dict):
                fallback_info = {"applied": False, "steps": []}
            
            tuition_values = [s.get("tuition", 0) for s in recommended_schools if s.get("tuition", 0) > 0]
            budget_range = ""
            if tuition_values:
                budget_range = f"推荐学校学费范围：S${min(tuition_values):,} - S${max(tuition_values):,}/年（USD约${int(min(tuition_values) * 0.74):,} - ${int(max(tuition_values) * 0.74):,}）"
            else:
                budget_range = "推荐学校学费范围：请查看具体学校信息"
            
            return {
                "id": str(evaluation.get("_id")),
                "user_id": str(evaluation.get("user_id")),
                "targetCountry": "Singapore",
                "recommendedSchools": schools_with_explanations,
                "fallbackInfo": fallback_info,
                "applicationGuidance": {
                    "title": "新加坡大学申请流程说明",
                    "steps": [
                        "1. 准备材料：高中成绩单、英语成绩（IELTS/TOEFL/PTE）、个人陈述、推荐信",
                        "2. 提交申请：通过各大学官网直接申请（无需统一系统）",
                        "3. 申请时间：多数大学10-11月开始接受申请，次年1-3月截止",
                        "4. 面试/作品集：部分专业需要面试、作品集或小论文（需提前准备）",
                        "5. Tuition Grant（TG）：如申请TG，需签约毕业后在新加坡工作若干年",
                        "6. 等待Offer：收到录取通知（有条件/无条件）",
                        "7. 接受Offer：按要求缴纳押金确认录取",
                        "8. 学生签证：申请新加坡学生准证（Student Pass）"
                    ],
                    "keyPoints": [
                        "申请系统：各大学独立申请系统，需分别提交材料",
                        "申请费：多数大学申请费约S$10-50（约USD 7-37）",
                        "TG申请：可在接受Offer后申请Tuition Grant，降低学费但需履行Bond服务期",
                        "面试要求：部分热门专业（如医学、法律、设计）需要面试或作品集",
                        "双学位：部分大学提供双学位项目，需额外申请或满足条件"
                    ]
                },
                "keyInfoSummary": {
                    "budgetRange": budget_range,
                    "tgInfo": "Tuition Grant可大幅降低学费，但需签约在新加坡工作若干年",
                    "applicationTiming": "主要申请时间：10-11月开始，次年1-3月截止",
                    "visaInfo": "学生准证有效期通常覆盖整个学习期间，毕业后可申请工作准证"
                },
                "created_at": evaluation.get("created_at")
            }
        elif input_country == "Australia":
            # 澳洲专用结构：生成解释和申请指导
            from gpt.au_evaluation import generate_school_explanations
            input_dict = evaluation.get("input") or {}
            if not isinstance(input_dict, dict):
                input_dict = {}
            
            schools_with_explanations = []
            for school in recommended_schools:
                school_id = school.get("id")
                if not school_id:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": 0,
                    })
                    continue
                
                school_detail = next((s for s in schools if str(s.get("_id")) == school_id), None)
                
                if school_detail:
                    try:
                        explanation = generate_school_explanations(school_detail, input_dict)
                        schools_with_explanations.append({
                            **school,
                            "explanation": explanation,
                            "matchScore": 0,  # GET接口不保存score，设为0
                        })
                    except Exception as e:
                        print(f"生成AU学校解释时出错: {e}")
                        schools_with_explanations.append({
                            **school,
                            "explanation": [],
                            "matchScore": 0,
                        })
                else:
                    schools_with_explanations.append({
                        **school,
                        "explanation": [],
                        "matchScore": 0,
                    })
            
            # 提取fallback信息（如果之前保存了）
            fallback_info = evaluation.get("fallback_info") or {"applied": False, "steps": []}
            if not isinstance(fallback_info, dict):
                fallback_info = {"applied": False, "steps": []}
            
            # 计算关键信息汇总
            tuition_values = [s.get("tuition", 0) for s in recommended_schools if s.get("tuition", 0) > 0]
            budget_range = ""
            if tuition_values:
                budget_range = f"推荐学校学费范围：${min(tuition_values):,} - ${max(tuition_values):,}/年（USD）"
            else:
                budget_range = "推荐学校学费范围：请查看具体学校信息"
            
            return {
                "id": str(evaluation.get("_id")),
                "user_id": str(evaluation.get("user_id")),
                "targetCountry": "Australia",
                "recommendedSchools": schools_with_explanations[:5],  # 限制最多5所
                "fallbackInfo": fallback_info,
                "applicationGuidance": {
                    "title": "澳洲大学申请流程说明",
                    "steps": [
                        "1. 准备材料：高中成绩单、英语成绩（IELTS/TOEFL/PTE）、个人陈述（部分学校需要）",
                        "2. 选择入学时间：多数学校提供2月和7月入学，部分提供3个学期",
                        "3. 直接申请：通过学校官网或授权代理申请（无需统一系统）",
                        "4. 语言班选项：如英语未达标，可申请语言/过渡课程，通过后进入正课",
                        "5. 接受Offer：收到录取后按要求缴纳押金并办理学生签证",
                        "6. 签证申请：准备资金证明、体检等材料，申请澳洲学生签证"
                    ],
                    "keyPoints": [
                        "申请时间灵活：通常提前3-6个月即可，部分热门专业需更早",
                        "英语成绩：大部分学校接受多种英语考试，可后补（部分专业除外）",
                        "申请费：多数学校申请免费或费用较低（约50-100澳元）"
                    ]
                },
                "keyInfoSummary": {
                    "budgetRange": budget_range,
                    "englishRequirement": "大部分学校要求IELTS 6.5（单项不低于6.0）或同等水平",
                    "intakeTiming": "主要入学时间：2月和7月",
                    "pswInfo": "毕业后可获得2-4年PSW工作签证（取决于学习时长和地区）"
                },
                "gptSummary": evaluation.get("gpt_summary", ""),  # 添加gptSummary字段
                "created_at": evaluation.get("created_at")
            }
        else:
            # 其他国家（USA）返回原有结构，需要分类ED/EA/RD
            from gpt.recommend_schools import classify_applications, generate_student_profile, generate_application_strategy
            from models.evaluation import ParentEvaluationInput
            
            ed_suggestion, ea_suggestions, rd_suggestions = classify_applications(recommended_schools)
            
            # 从数据库读取的input数据重新生成学生画像和申请策略
            input_dict = evaluation.get("input") or {}
            if not isinstance(input_dict, dict):
                input_dict = {}
            
            try:
                # 将字典转换为ParentEvaluationInput对象
                input_data = ParentEvaluationInput(**input_dict)
                student_profile = generate_student_profile(input_data)
                strategy_text = generate_application_strategy(input_data, len(recommended_schools))
            except Exception as e:
                print(f"⚠️ 生成学生画像或申请策略时出错: {e}")
                student_profile = {"type": "", "description": ""}
                strategy_text = ""
            
            strategy = {"plan": strategy_text, "count": len(recommended_schools)}
            
            return {
                "id": str(evaluation.get("_id")),
                "user_id": str(evaluation.get("user_id")),
                "studentProfile": student_profile,
                "recommendedSchools": recommended_schools,
                "edSuggestion": ed_suggestion,
                "eaSuggestions": ea_suggestions,
                "rdSuggestions": rd_suggestions,
                "strategy": strategy,
                "gptSummary": evaluation.get("gpt_summary", ""),
                "created_at": evaluation.get("created_at")
            }
    except Exception as e:
        print(f"获取评估结果时出错: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取评估结果时出错: {str(e)}")

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
    
    # Convert to dict without the id field to avoid _id: null issue
    test_dict = test.dict(by_alias=True, exclude={'id'})
    result = await db.student_personality_tests.insert_one(test_dict)
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