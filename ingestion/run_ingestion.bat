@echo off
echo ========================================
echo Starting Batch Ingestion Pipeline
echo ========================================
echo Note: Contextual Retrieval is ENABLED for all 7 files.
echo If AWS rate limits are hit, the script will pause for 60 seconds and retry (up to 7 times).
echo.

echo [1/7] Ingesting fever_under_5s.md (Redoing to get full context)...
python run_ingestion.py --file data/fever_under_5s.md --source NICE
echo.

echo [2/7] Ingesting infant_feeding_problems.md...
python run_ingestion.py --file data/infant_feeding_problems.md --source AAP
echo.

echo [3/7] Ingesting childhood_rashes.md...
python run_ingestion.py --file data/childhood_rashes.md --source WHO
echo.

echo [4/7] Ingesting respiratory_distress_under_5s.md...
python run_ingestion.py --file data/respiratory_distress_under_5s.md --source CDC
echo.

echo [5/7] Ingesting general_newborn_care.md...
python run_ingestion.py --file data/general_newborn_care.md --source WHO
echo.

echo [6/7] Ingesting newborn_care_until_the_first_week_of_life.md...
python run_ingestion.py --file data/newborn_care_until_the_first_week_of_life.md --source WHO
echo.

echo [7/7] Ingesting recommendations_for_management_of_common_childhood_conditions.md...
python run_ingestion.py --file data/recommendations_for_management_of_common_childhood_conditions.md --source WHO
echo.

echo ========================================
echo ALL INGESTIONS COMPLETED SUCCESSFULLY!
echo ========================================
pause
