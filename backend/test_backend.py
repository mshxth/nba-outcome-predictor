"""Test script for Flask backend - run AFTER copying files."""

import sys
import os

print("="*60)
print("FLASK BACKEND TEST")
print("="*60)

# Test 1: Check required files
print("\n[Test 1] Checking required files...")

required_files = [
    'config.py',
    'data.py', 
    'database.py',
    'data/nba_data.db',
    'models/trained_model.pkl'
]

missing = []
for file in required_files:
    if not os.path.exists(file):
        missing.append(file)
        print(f"❌ Missing: {file}")
    else:
        print(f"✅ Found: {file}")

if missing:
    print("\n⚠️  Missing files! Please copy them:")
    print("\nFrom your project root:")
    print("cp config.py backend/")
    print("cp data.py backend/")
    print("cp database.py backend/")
    print("cp nba_data.db backend/data/")
    print("cp trained_model.pkl backend/models/")
    print("cp -r TEAMS backend/")
    sys.exit(1)

# Test 2: Try importing modules
print("\n[Test 2] Testing imports...")
try:
    from ml_model import load_model, predict_game_outcome
    print("✅ ML model imports work")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 3: Load model
print("\n[Test 3] Loading model...")
try:
    model_data = load_model()
    print(f"✅ Model loaded")
    print(f"   Accuracy: {model_data.get('accuracy', 0)*100:.2f}%")
except Exception as e:
    print(f"❌ Model load failed: {e}")
    sys.exit(1)

# Test 4: Test prediction
print("\n[Test 4] Testing prediction...")
try:
    winner, confidence = predict_game_outcome("Detroit", "New York", model_data)
    print(f"✅ Prediction works")
    print(f"   Winner: {winner}")
    print(f"   Confidence: {confidence*100:.1f}%")
except Exception as e:
    print(f"❌ Prediction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "="*60)
print("ALL TESTS PASSED!")
print("="*60)
print("\nNext step: Start the Flask server")
print("Run: python3 app.py")
print("Then visit: http://localhost:8000")
print("="*60)