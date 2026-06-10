import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, accuracy_score 
import joblib 

# 1. Load your data
df = pd.read_csv("complaints_data.csv") 
df.columns = df.columns.str.strip().str.lower()
df['category'] = df['category'].str.strip()

X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    df['text'], df['category'], test_size=0.2, random_state=42
)

# 2. Convert text to numbers
vectorizer = TfidfVectorizer()
X_train = vectorizer.fit_transform(X_train_raw) 
X_test = vectorizer.transform(X_test_raw)     

# 3. Train the model
model = MultinomialNB()
model.fit(X_train, y_train)

# ---CHECK ACCURACY ------------------
y_pred = model.predict(X_test)
print("\n" + "="*30)
print(f"OVERALL ACCURACY: {accuracy_score(y_test, y_pred)*100:.2f}%")
print("="*30)
print("DETAILED REPORT PER DEPARTMENT:")
print(classification_report(y_test, y_pred)) # Shows Precision, Recall, F1
print("="*30 + "\n")

# 4. SAVE the model and the vectorizer
full_vectorizer = TfidfVectorizer().fit(df['text'])
full_model = MultinomialNB().fit(full_vectorizer.transform(df['text']), df['category'])

joblib.dump(full_model, 'model.pkl')
joblib.dump(full_vectorizer, 'vectorizer.pkl')
print("Fresh Model trained and saved!")