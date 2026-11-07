"""Source identities and visual review observations, not canned question answers.

Titles, years, totals and representative rows below were checked against
rendered supplied PDF pages. Reviews are AI visual checks; human sign-off is
separate. Import binds these observations to the recorded source SHA256.
"""
PLANS = [
    {'id':'hu-cs-2022','filename':'بكالوريوس علم الحاسوب 2022.pdf','program_id':'hu-cs',
     'name_ar':'علم الحاسوب','name_en':'Computer Science','year':2022,'total_credits':135,
     'warnings':['Source page 1 labels university requirements 28 credits, while its mandatory/elective subtotals are 19 and 6. Do not repair or infer a reconciled total.'],
     'reviewed_rows':[(1,'10100',3,'-'),(1,'T1100',3,'-'),(3,'T1214',3,'T1229'),(3,'T1315',3,'T1214'),(3,'T1225',1,'+ T1214')]},
    {'id':'hu-cs-ai-2024','filename':'تخصص رئيسي علم الحاسوب فرعي علم البيانات والذكاء الاصطناعي 2024.pdf',
     'program_id':'hu-cs-ai','name_ar':'رئيسي علم الحاسوب / فرعي علم البيانات والذكاء الاصطناعي',
     'name_en':'Major Computer Science / Minor Data Science and Artificial Intelligence','year':2024,'total_credits':138,
     'reviewed_rows':[(1,'10100',3,'-'),(1,'T1100',3,'-'),(3,'T1211',3,'T1229/41130'),(3,'T1345',3,'T1344')]},
    {'id':'hu-cs-se-2026','filename':'بكالوريوس رئيسي علم حاسوب – فرعي هندسة برمجيات 2026.pdf',
     'program_id':'hu-cs-se','name_ar':'رئيسي علم الحاسوب / فرعي هندسة برمجيات',
     'name_en':'B.Sc. in Computer Science - Minor Software Engineering','year':2026,'total_credits':138,
     'reviewed_rows':[(1,'10100',3,'-'),(1,'T1100',3,'-'),(3,'T1112',3,'T1111'),(3,'T1229',3,'T1112')]},
    {'id':'hu-cs-business-2022','filename':'بكالوريوس رئيسي علم الحاسوب- فرعي ادارة الاعمال 2022.pdf',
     'program_id':'hu-cs-business','name_ar':'رئيسي علم الحاسوب / فرعي إدارة الأعمال',
     'name_en':'Major Computer Science / Minor Business Administration','year':2022,'total_credits':138,
     'reviewed_rows':[(1,'10100',3,'-'),(1,'T1100',3,'-'),(1,'61200',2,'-')]},
    {'id':'hu-web-2022','filename':'بكالوريوس تكنولوجيا الويب والوسائط المتعددة 2022.pdf',
     'program_id':'hu-web','name_ar':'تكنولوجيا الويب والوسائط المتعددة','name_en':'Web Technology and Multimedia',
     'year':2022,'total_credits':135,'warnings':['Source page 1 university-requirement heading 28 differs from 19 + 6 listed subtotals.'],
     'reviewed_rows':[(1,'10100',3,'-'),(1,'T1100',3,'-'),(1,'61200',2,'-')]},
    {'id':'hu-cyber-2022','filename':'بكالوريوس الأمن السيبراني 2022.pdf','program_id':'hu-cyber',
     'name_ar':'الأمن السيبراني','name_en':'CyberSecurity','year':2022,'total_credits':133,
     'warnings':['Source university-requirement heading is 24, mandatory heading 18, while the displayed seven mandatory rows sum to 19. Preserve the printed source and seek institutional clarification.',
                 'Course 61101 is printed as 2 credits on PDF page 1 and 3 credits on PDF page 2. Do not choose one value or merge the two observations.'],
     'reviewed_rows':[(1,'10100',3,'-'),(1,'T1100',3,'-'),(1,'61101',2,'-')]},
    {'id':'hu-cybercrime-2022','filename':'بكالوريوس الأمن السيبراني- مسار جرائم الكترونية 2022.pdf',
     'program_id':'hu-cybercrime','name_ar':'الأمن السيبراني / مسار التحقيق في الجرائم الإلكترونية',
     'name_en':'Cyber Security / Cybercrimes Investigation','year':2022,'total_credits':134,
     'reviewed_rows':[(1,'10100',3,'-'),(1,'T1100',3,'-'),(1,'61200',2,'-')]},
]

# Catalog descriptions identify a blank form's purpose only. They establish no
# current deadline, entitlement, refund right or eligibility regulation.
FORMS = {
    '014':('نموذج تقديم عذر الغياب عن امتحان نهائي','تقديم عذر عن الغياب عن امتحان نهائي','غياب امتحان نهائي عذر final exam absence excuse'),
    '015':('نموذج الموافقة على تقديم امتحان نهائي غير مكتمل','توثيق الموافقة على تقديم امتحان نهائي غير مكتمل','امتحان غير مكتمل incomplete final exam'),
    '016':('نموذج تسجيل مساق بديل للتخرج','طلب تسجيل مساق بديل للتخرج','بديل مساق تخرج substitute course graduation'),
    '017':('نموذج المساقات المتبقية (للطلبة المتوقع تخرجهم)','حصر المساقات والساعات المتبقية للطلبة المتوقع تخرجهم','متبقية متبقي تخرج remaining courses graduation'),
    '018':('نموذج تخريج طالب','توثيق طلب أو إجراء تخريج طالب','تخريج تخرج graduation student'),
    '020':('نموذج سحب فصل دراسي','طلب سحب فصل دراسي','سحب فصل انسحاب semester withdrawal'),
    '021':('نموذج تأجيل فصل','طلب تأجيل فصل دراسي','تأجيل تاجيل تأخير فصل semester deferral defer postpone'),
    '022':('نموذج معادلة المساقات للانتقال من جامعة أخرى إلى جامعة الخليل','توثيق معادلة مساقات عند الانتقال من جامعة أخرى إلى جامعة الخليل','معادلة انتقال تحويل جامعة أخرى جامعات equivalency transfer universities'),
    '023':('نموذج معادلة المساقات للانتقال من كلية إلى كلية في الجامعة','توثيق معادلة المساقات للانتقال بين كليات الجامعة','معادلة انتقال كلية كليات faculties college'),
    '024':('نموذج معادلة المساقات للانتقال من قسم إلى قسم في الجامعة','توثيق معادلة المساقات للانتقال بين الأقسام','معادلة انتقال قسم اقسام department'),
    '027':('نموذج عرض حال','عرض طلب أو موضوع على عميد الكلية','عرض حال عميد التماس شكوى استرحام appeal dean petition'),
    '031':('نموذج معادلة المساقات للتجسير من الدبلوم إلى البكالوريوس','توثيق معادلة مساقات التجسير من الدبلوم للبكالوريوس','معادلة تجسير دبلوم بكالوريوس diploma bachelor bridging'),
}

# English renderings of the visually reviewed Arabic form titles/purposes.
# Original Arabic titles remain unchanged in citations and the source PDFs.
FORMS_EN = {
    '014':('Final examination absence excuse form','Submit an excuse for absence from a final examination'),
    '015':('Approval to take an incomplete final examination','Record approval to take an incomplete final examination'),
    '016':('Substitute course registration for graduation','Request registration in a substitute course for graduation'),
    '017':('Remaining courses for expected graduates','List the courses and credits remaining for an expected graduate'),
    '018':('Student graduation form','Document a student graduation request or procedure'),
    '020':('Semester withdrawal form','Request withdrawal from a semester'),
    '021':('Semester deferral form','Request deferral of a semester'),
    '022':('Course equivalency for transfer from another university to Hebron University','Document course equivalency when transferring from another university to Hebron University'),
    '023':('Course equivalency for transfer between colleges','Document course equivalency when transferring between colleges within the university'),
    '024':('Course equivalency for transfer between departments','Document course equivalency when transferring between departments within the university'),
    '027':('Petition to the dean','Present a request or matter to the college dean'),
    '031':('Course equivalency for bridging from diploma to bachelor degree','Document course equivalency when bridging from a diploma to a bachelor degree'),
}

EXCLUSIONS = {
    '019-form.pdf':'Graduate-studies language review; outside the IT undergraduate MVP.',
    '032-form.pdf':'Medical-college annual deferral; outside the IT undergraduate MVP.',
    'Academic-Advisory-General Division.pdf':'Faculty of Law advisory plan; outside the IT knowledge corpus.',
}

EXCLUDED_METADATA = {
    '019-form.pdf':('graduate_language_review_form','تدقيق لغوي (عربي، انجليزي) — الدراسات العليا'),
    '032-form.pdf':('medical_annual_deferral_form','نموذج تأجيل عام دراسي (كلية الطب)'),
    'Academic-Advisory-General Division.pdf':('law_advisory_plan','الخطة الإرشادية الأكاديمية — كلية الحقوق / قسم القانون العام'),
}
