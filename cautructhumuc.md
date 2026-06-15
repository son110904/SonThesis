career_guidance/
├── data/
│   ├── VietJobs_JD.csv
│   ├── job_resume_fit.csv
│   └── occupation_profiles/        # (trống, chờ Bước 10)
│
├── models/                         # (trống, chờ Bước 8)
│
└── src/
    ├── __init__.py
    ├── config.py                   # Tham số tập trung toàn hệ thống
    │
    └── offline/
        ├── preprocessing/          # Bước 1 ✅
        │   ├── __init__.py
        │   ├── data_loader.py
        │   └── text_cleaner.py
        │
        ├── skill_extraction/       # Bước 2 ✅
        │   ├── __init__.py
        │   └── extractor.py
        │
        ├── profile_builder/        # Bước 3 ✅
        │   ├── __init__.py
        │   └── occupation_profile_builder.py
        │
        ├── frequency_analysis/     # Bước 4 
        ├── tfidf_analysis/         # Bước 5 
        ├── skill_weight/           # Bước 6 
        ├── embedding/              # Bước 8
        └── knowledge_base/         # Bước 9 (chưa làm)

    training/                       # Bước 7 (chưa làm)