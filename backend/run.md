# 1. Ensure you are in the project root
cd D:\OCR\HBS-OCR-Tool
 
# 2. Create the virtual environment
python -m venv venv
 
# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1
 
# 4. Install backend dependencies
pip install -r backend/requirements.txt
 
# 5. Run the application
python run.py